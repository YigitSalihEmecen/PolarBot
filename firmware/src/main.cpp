#include <AccelStepper.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WebSocketsServer.h>
#include <WiFiManager.h>

// Using your confirmed working pin sequences
AccelStepper plateStepper(AccelStepper::HALF4WIRE, 5, 14, 4, 12);
AccelStepper armStepper(AccelStepper::HALF4WIRE, 13, 16, 3,
                        1); // Pins 1 and 3 are now completely free from Serial!

// Backlash compensation (deadzone) in steps (Now dynamically adjustable!)
int PLATE_BACKLASH = 80;
int ARM_BACKLASH = 100;

// Hardware Conversion Constants
const float PLATE_STEPS_PER_REV = 13920.0;
const float STEPS_PER_MM_ARM =
    -3800.0 / 66.0; // Negated to reverse drawing direction

bool doingBacklash = false;
bool isFirstMove = true;
bool isAbsoluteMode = true; // G90 default

long nextPlateLogical = 0;
long nextArmLogical = 0;

long currentPlateLogical = 0;
long currentArmLogical = 0;
int plateDir = 1;
int armDir = 1;
long lastPlateSteps = 0;

// Logical position in strictly MILLIMETERS
float current_x_mm = 0.0;
float current_y_mm = 0.0;
float target_x_mm = 0.0;
float target_y_mm = 0.0;

int currentChunk = 0;
int numChunks = 0;

// G-CODE BUFFER
const int BUFFER_SIZE = 8;
String gcodeBuffer[BUFFER_SIZE];
int bufferHead = 0;
int bufferTail = 0;
int bufferCount = 0;

// WiFi & WebSockets
WebSocketsServer webSocket = WebSocketsServer(81);
uint8_t activeClientNum = 255;

void webSocketEvent(uint8_t num, WStype_t type, uint8_t *payload,
                    size_t length) {
  switch (type) {
  case WStype_DISCONNECTED:
    if (activeClientNum == num)
      activeClientNum = 255;
    break;
  case WStype_CONNECTED:
    activeClientNum = num;
    break;
  case WStype_TEXT:
    // We received a G-code line!
    if (bufferCount < BUFFER_SIZE) {
      String incomingLine = String((char *)payload);
      incomingLine.trim();
      if (incomingLine.length() > 0) {
        gcodeBuffer[bufferHead] = incomingLine;
        bufferHead = (bufferHead + 1) % BUFFER_SIZE;
        bufferCount++;
      }
    }
    break;
  }
}

// Converts Cartesian mm (X,Y) to Polar Stepper targets
void cartesianToPolarSteps(float x_mm, float y_mm, long &outPlateSteps,
                           long &outArmSteps) {
  float r_mm = sqrt(x_mm * x_mm + y_mm * y_mm);
  // Negate theta to fix the mirrored image hardware issue
  float theta = -atan2(y_mm, x_mm);

  if (r_mm < 0.1) {
    outPlateSteps = lastPlateSteps;
    outArmSteps = 0;
    return;
  }

  float last_theta = (lastPlateSteps * 2.0 * PI) / PLATE_STEPS_PER_REV;
  while (theta - last_theta > PI)
    theta -= 2.0 * PI;
  while (theta - last_theta < -PI)
    theta += 2.0 * PI;

  long rawPlateSteps = round((theta / (2.0 * PI)) * PLATE_STEPS_PER_REV);
  outPlateSteps = rawPlateSteps;
  outArmSteps = round(r_mm * STEPS_PER_MM_ARM);
  lastPlateSteps = rawPlateSteps;
}

void parseGcodeLine(String line) {
  // Strip comments
  int commentIdx = line.indexOf('(');
  if (commentIdx != -1)
    line = line.substring(0, commentIdx);
  commentIdx = line.indexOf(';');
  if (commentIdx != -1)
    line = line.substring(0, commentIdx);
  line.trim();
  line.toUpperCase();
  if (line.length() == 0)
    return;

  if (line.indexOf("M100") != -1) {
    // Custom command to update backlash settings over WiFi!
    int pIdx = line.indexOf('P');
    if (pIdx != -1)
      PLATE_BACKLASH = line.substring(pIdx + 1).toInt();
    int aIdx = line.indexOf('A');
    if (aIdx != -1)
      ARM_BACKLASH = line.substring(aIdx + 1).toInt();
    if (activeClientNum != 255) {
      String msg = "Backlash updated: P" + String(PLATE_BACKLASH) + " A" +
                   String(ARM_BACKLASH);
      webSocket.sendTXT(activeClientNum, msg);
    }
    return;
  }

  if (line.indexOf("M101") != -1) {
    // Custom command to physically home the arm
    armStepper.setMaxSpeed(800.0);
    armStepper.setAcceleration(2000.0);
    armStepper.move(4000); // 4000 steps to extend the arm towards the center
    unsigned long startTime = millis();
    while (millis() - startTime < 4000) {
      armStepper.run();
      webSocket.loop(); // Keep connection alive
      yield();
    }
    plateStepper.setCurrentPosition(0);
    armStepper.setCurrentPosition(0);
    currentPlateLogical = 0;
    currentArmLogical = 0;
    nextPlateLogical = 0;
    nextArmLogical = 0;
    current_x_mm = 0.0;
    current_y_mm = 0.0;
    target_x_mm = 0.0;
    target_y_mm = 0.0;
    armStepper.setAcceleration(100000.0);

    if (activeClientNum != 255) {
      webSocket.sendTXT(activeClientNum, "Homing Complete!");
    }
    return;
  }

  if (line.indexOf("M30") != -1 || line.indexOf("M0") != -1 ||
      line.indexOf("M2") != -1) {
    return;
  }

  if (line.indexOf("G90") != -1) {
    isAbsoluteMode = true;
    return;
  }
  if (line.indexOf("G91") != -1) {
    isAbsoluteMode = false;
    return;
  }

  if (line.indexOf("G28") != -1) {
    // Home command
    target_x_mm = 0.0;
    target_y_mm = 0.0;
    float dx = target_x_mm - current_x_mm;
    float dy = target_y_mm - current_y_mm;
    float dist = sqrt(dx * dx + dy * dy);
    if (dist > 0.01) {
      numChunks = max(1, (int)ceil(dist / 0.2));
      currentChunk = 0;
    }
    return;
  }

  if (line.indexOf("G0") != -1 || line.indexOf("G1") != -1) {
    bool hasMovement = false;
    float new_x = target_x_mm;
    float new_y = target_y_mm;

    int xIdx = line.indexOf('X');
    if (xIdx != -1) {
      float val = line.substring(xIdx + 1).toFloat();
      new_x = isAbsoluteMode ? val : (current_x_mm + val);
      hasMovement = true;
    }

    int yIdx = line.indexOf('Y');
    if (yIdx != -1) {
      float val = line.substring(yIdx + 1).toFloat();
      new_y = isAbsoluteMode ? val : (current_y_mm + val);
      hasMovement = true;
    }

    if (hasMovement) {
      current_x_mm = target_x_mm;
      current_y_mm = target_y_mm;
      target_x_mm = new_x;
      target_y_mm = new_y;

      float dx = target_x_mm - current_x_mm;
      float dy = target_y_mm - current_y_mm;
      float dist = sqrt(dx * dx + dy * dy);

      // --- ORIGIN PRE-ROTATION FIX ---
      if (abs(current_x_mm) < 0.1 && abs(current_y_mm) < 0.1 && dist > 0.1) {
        float theta = -atan2(target_y_mm, target_x_mm);
        float last_theta = (lastPlateSteps * 2.0 * PI) / PLATE_STEPS_PER_REV;
        while (theta - last_theta > PI)
          theta -= 2.0 * PI;
        while (theta - last_theta < -PI)
          theta += 2.0 * PI;
        long targetPlateSteps =
            round((theta / (2.0 * PI)) * PLATE_STEPS_PER_REV);

        if (targetPlateSteps != currentPlateLogical) {
          plateStepper.setMaxSpeed(800.0);
          plateStepper.setAcceleration(100000.0);
          plateStepper.moveTo(targetPlateSteps);
          while (plateStepper.distanceToGo() != 0) {
            plateStepper.run();
            // Important to yield and process websockets even during
            // pre-rotation
            webSocket.loop();
            yield();
          }
          lastPlateSteps = targetPlateSteps;
          currentPlateLogical = targetPlateSteps;
          nextPlateLogical = targetPlateSteps;
        }
      }

      numChunks = max(1, (int)ceil(dist / 0.2));
      currentChunk = 0;
    }
  }
}

void setup() {
  // NO Serial.begin()! We are completely freeing Pins 1 and 3 for the
  // armStepper!

  // 1. Wait for power to physically stabilize on the NodeMCU board
  delay(1000);

  // 2. Setup Steppers
  plateStepper.setMaxSpeed(800.0);
  plateStepper.setAcceleration(100000.0);

  // Use a much gentler acceleration curve for homing to prevent stalls/noise!
  armStepper.setMaxSpeed(800.0);
  armStepper.setAcceleration(2000.0);

  // --- HOMING SEQUENCE ---
  // We use .move() and .run() instead of .runSpeed() so it actually uses
  // acceleration! This prevents the violent jump to 800 RPM that causes the
  // motor to whine and stall.
  armStepper.move(4000); // 4000 steps to extend the arm towards the hard center
  unsigned long startTime = millis();
  while (millis() - startTime < 5000) {
    armStepper.run();
    yield();
  }

  // Set the mechanical zero point
  plateStepper.setCurrentPosition(0);
  armStepper.setCurrentPosition(0);

  // Restore the super high acceleration for drawing operations
  armStepper.setAcceleration(100000.0);

  // 3. NOW start WiFiManager!
  // We start it AFTER the motors are done homing to prevent brownouts.
  WiFiManager wifiManager;
  // This blocks until connected or a new network is configured
  wifiManager.autoConnect("PolarPlotter-Setup");

  // Setup mDNS so the Web App can connect to ws://polarplotter.local:81
  if (MDNS.begin("polarplotter")) {
    MDNS.addService("ws", "tcp", 81);
  }

  // Start WebSocket server
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
}

void loop() {
  MDNS.update();

  // Process incoming WiFi WebSocket data
  webSocket.loop();

  // 1. If we are currently executing an active G-code line
  if (numChunks > 0 && currentChunk <= numChunks) {
    long lookahead = 0;
    if (!doingBacklash && currentChunk < numChunks) {
      lookahead = 2;
    }

    if (abs(plateStepper.distanceToGo()) <= lookahead &&
        abs(armStepper.distanceToGo()) <= lookahead) {

      if (doingBacklash) {
        doingBacklash = false;

        long physicalTargetPlate =
            nextPlateLogical + (plateDir == 1 ? PLATE_BACKLASH : 0);
        long physicalTargetArm =
            nextArmLogical + (armDir == 1 ? ARM_BACKLASH : 0);

        long dPlate = abs(physicalTargetPlate - plateStepper.currentPosition());
        long dArm = abs(physicalTargetArm - armStepper.currentPosition());
        long maxDist = max(dPlate, dArm);

        if (maxDist > 0) {
          float plateRatio = (float)dPlate / maxDist;
          float armRatio = (float)dArm / maxDist;

          plateStepper.setMaxSpeed(max(800.0 * plateRatio, 20.0));
          plateStepper.setAcceleration(max(100000.0 * plateRatio, 20.0));
          armStepper.setMaxSpeed(max(800.0 * armRatio, 20.0));
          armStepper.setAcceleration(max(100000.0 * armRatio, 20.0));
        }

        plateStepper.moveTo(physicalTargetPlate);
        armStepper.moveTo(physicalTargetArm);
        currentPlateLogical = nextPlateLogical;
        currentArmLogical = nextArmLogical;

      } else {
        currentChunk++;

        if (currentChunk > numChunks) {
          numChunks = 0;
        } else {
          float t = (float)currentChunk / numChunks;
          float x_mm = current_x_mm + (target_x_mm - current_x_mm) * t;
          float y_mm = current_y_mm + (target_y_mm - current_y_mm) * t;

          cartesianToPolarSteps(x_mm, y_mm, nextPlateLogical, nextArmLogical);

          int newPlateDir = plateDir;
          if (nextPlateLogical > currentPlateLogical)
            newPlateDir = 1;
          else if (nextPlateLogical < currentPlateLogical)
            newPlateDir = -1;

          int newArmDir = armDir;
          if (nextArmLogical > currentArmLogical)
            newArmDir = 1;
          else if (nextArmLogical < currentArmLogical)
            newArmDir = -1;

          long pBacklash = 0;
          long aBacklash = 0;

          if (newPlateDir != plateDir &&
              nextPlateLogical != currentPlateLogical) {
            pBacklash = (newPlateDir == 1) ? PLATE_BACKLASH : -PLATE_BACKLASH;
            plateDir = newPlateDir;
          }
          if (newArmDir != armDir && nextArmLogical != currentArmLogical) {
            aBacklash = (newArmDir == 1) ? ARM_BACKLASH : -ARM_BACKLASH;
            armDir = newArmDir;
          }

          if (isFirstMove) {
            pBacklash = PLATE_BACKLASH;
            aBacklash = ARM_BACKLASH;
            plateDir = 1;
            armDir = 1;
            isFirstMove = false;
          }

          if (pBacklash != 0 || aBacklash != 0) {
            plateStepper.setMaxSpeed(800.0);
            plateStepper.setAcceleration(100000.0);
            armStepper.setMaxSpeed(800.0);
            armStepper.setAcceleration(100000.0);

            plateStepper.move(pBacklash);
            armStepper.move(aBacklash);
            doingBacklash = true;
          } else {
            long physicalTargetPlate =
                nextPlateLogical + (plateDir == 1 ? PLATE_BACKLASH : 0);
            long physicalTargetArm =
                nextArmLogical + (armDir == 1 ? ARM_BACKLASH : 0);

            long dPlate =
                abs(physicalTargetPlate - plateStepper.currentPosition());
            long dArm = abs(physicalTargetArm - armStepper.currentPosition());
            long maxDist = max(dPlate, dArm);

            if (maxDist > 0) {
              float plateRatio = (float)dPlate / maxDist;
              float armRatio = (float)dArm / maxDist;

              plateStepper.setMaxSpeed(max(800.0 * plateRatio, 20.0));
              plateStepper.setAcceleration(max(100000.0 * plateRatio, 20.0));
              armStepper.setMaxSpeed(max(800.0 * armRatio, 20.0));
              armStepper.setAcceleration(max(100000.0 * armRatio, 20.0));
            }

            plateStepper.moveTo(physicalTargetPlate);
            armStepper.moveTo(physicalTargetArm);
            currentPlateLogical = nextPlateLogical;
            currentArmLogical = nextArmLogical;
          }
        }
      }
    }
  }

  // 2. IDLE STATE: If we need a new line, pull it from the buffer instantly!
  if (numChunks == 0 && bufferCount > 0) {
    String lineToParse = gcodeBuffer[bufferTail];
    bufferTail = (bufferTail + 1) % BUFFER_SIZE;
    bufferCount--;

    // Send "ok" over WiFi so the Web App sends the next line!
    if (activeClientNum != 255) {
      webSocket.sendTXT(activeClientNum, "ok");
    }

    parseGcodeLine(lineToParse);

    // If it was a movement line, start drawing it IMMEDIATELY on the next loop
    // iteration!
    if (numChunks > 0) {
      currentChunk = 1;
    }
  }

  // Non-blocking continuous motor execution!
  plateStepper.run();
  armStepper.run();
}