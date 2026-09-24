# The Polar Plotter Project: Definitive System Architecture & Developer Guide

## Abstract

The Polar Plotter is a custom-built 2-axis CNC drawing machine. Unlike a traditional Cartesian 3D printer or plotter that moves along perpendicular X and Y axes, this machine operates entirely in **Polar Coordinates**. It creates two-dimensional drawings by combining the continuous rotation of a central build plate (Theta) with the linear extension and retraction of an arm (Radius).

This architecture necessitates highly specialized firmware to translate standard Cartesian G-code into Polar geometry in real-time, handle complex mechanical backlash, and manage continuous data streaming over a local WiFi network without overwhelming the limited RAM of an ESP8266 microcontroller.

This document serves as the exhaustive, definitive reference manual for understanding every layer of the system.

---

## 1. Physical Hardware & Electronics

### Microcontroller & Motors
The brain of the system is the **NodeMCU v2 ESP8266** microcontroller, chosen for its built-in WiFi capabilities and low cost.
The physical movement is driven by two **28BYJ-48 Stepper Motors**, which are controlled by **ULN2003** Darlington transistor array driver boards.
Both driver boards take their 5V and GND directly from the NodeMCU, so the entire machine is powered from a single USB port. No separate power supply is used.

### Half-Step Sequencing (`HALF4WIRE`)
The `AccelStepper` library is configured to use `HALF4WIRE` mode. Instead of firing one coil at a time (full stepping), the driver alternates between firing one coil and two coils simultaneously. This doubles the resolution of the motor from 2048 steps per revolution to 4096 steps per revolution, providing incredibly smooth and precise drawing capabilities at the cost of slightly lower top speed.

### The TX/RX Hardware Conflict (The "Whining Motor" Bug)
Early in the project's lifecycle, the ESP8266 communicated with the control interface using standard USB Serial (`Serial.begin(115200)`). 
Due to the limited number of GPIO pins on the ESP8266, the linear arm motor was wired to Pins 1 (TX) and 3 (RX). However, on NodeMCU development boards, these specific pins are physically hardwired to the onboard USB-to-Serial converter chip (such as the CH340 or CP2102). 
When the firmware attempted to pulse these pins to step the motor, the USB-to-Serial chip would electrically "fight" the ESP8266, pulling the voltage in opposite directions. This completely crippled the arm motor—it lost all torque, made high-pitched whining noises, and stuttered violently.
**The Fix:** We completely removed the `Serial` library from the C++ code. By transitioning the entire communication stack to wireless WiFi WebSockets, Pins 1 and 3 were liberated, restoring 100% of the arm motor's torque and allowing it to function normally.

### Power Brownouts & Boot Sequencing
When the ESP8266 activates its WiFi radio, it draws a massive spike of electrical current (up to 400mA). Simultaneously, stepping the 28BYJ-48 motors draws significant current.
In earlier firmware versions, the homing sequence and the WiFi radio started at the exact same millisecond. This caused a catastrophic voltage drop (a "Brownout"), instantly crashing and rebooting the ESP8266 before the WiFi network could even broadcast.
**The Fix:** The `setup()` function was rewritten to enforce a strict sequence:
1. A 1000ms `delay()` to allow the physical power supply capacitors to charge.
2. The mechanical homing sequence runs to completion.
3. Only *after* the motors stop moving does the firmware start `WiFiManager` (`autoConnect()`), which turns on the radio.

### Motor Inertia & Acceleration Profiles
Stepper motors cannot instantly jump to high speeds. Initially, the homing sequence used `armStepper.runSpeed()` at 800 RPM. This bypassed the physical acceleration curves, causing the internal magnetic field of the motor to slip past the rotor (stalling).
**The Fix:** The homing sequence now uses `armStepper.move(4000)` combined with a gentle acceleration limit of `2000.0 steps/sec²`. This allows the physical mass of the arm to smoothly ramp up to speed.

---

## 2. Network & Communication Architecture

### WiFiManager: The Smart-Device Paradigm
Hardcoding the user's home WiFi SSID and Password into the C++ source code is inflexible; if the router password changes, the firmware must be recompiled. 
To solve this, we implemented the `WiFiManager` library. 
When the ESP8266 powers on, it checks a hidden sector in its flash memory for saved WiFi credentials. If none are found, or if it cannot connect, it shifts into Access Point mode and broadcasts its own unencrypted WiFi network called `"PolarPlotter-Setup"`. 
When the user connects to this network with a smartphone, a Captive Portal pops up. The user selects their home network from a list, types the password, and clicks Save. The ESP8266 stores these credentials permanently and reboots, connecting to the home network like a commercial smart bulb.

### mDNS (Bonjour) Resolution
Once the ESP8266 connects to the home router, it is assigned a random IP address via DHCP. Without a Serial monitor, the user has no way of knowing what this IP address is.
To bypass this, we utilize the `ESP8266mDNS` library. During boot, the ESP8266 broadcasts a multicast signal declaring its hostname: `polarplotter.local`. 
The operating systems of devices on the network (macOS Bonjour, Windows mDNSResponder) automatically intercept this broadcast. This allows the Web App to blindly attempt a WebSocket connection to `ws://polarplotter.local:81` without ever needing to know the actual IP address.

### WebSockets & The Ping-Pong Protocol
A `.gcode` file can easily exceed 50,000 lines of text. The ESP8266 only has ~80KB of RAM and cannot store the entire file. We cannot use standard HTTP POST requests, as the overhead of opening and closing TCP connections for every single line of G-code would introduce massive latency and stuttering.
Instead, we use a single, persistent **WebSocket** connection.
To manage the flow of data, we use a "Ping-Pong" handshake:
1. The Web App fires up to 4 lines of G-code over the socket.
2. The ESP8266 places them in its tiny internal buffer.
3. Every time the ESP8266 finishes processing a line and removes it from the buffer, it transmits the string `"ok"` back over the WebSocket.
4. The Web App counts every line it has sent (including manual `M100`/`M101` commands) and every `"ok"` it has received. Whenever fewer than 4 lines are in flight, it sends the next one.
This guarantees that the ESP8266's tiny RAM is never over-filled, while ensuring it always has the next physical movement pre-loaded to prevent mechanical stuttering.

---

## 3. The Firmware: Execution Loop & The Circular Buffer

The C++ firmware is built around a strictly asynchronous, non-blocking state machine. 

### The Circular Buffer Array
```cpp
const int BUFFER_SIZE = 8;
String gcodeBuffer[BUFFER_SIZE];
int bufferHead = 0;
int bufferTail = 0;
int bufferCount = 0;
```
As WebSocket packets arrive in the background, the `webSocketEvent` callback (run from `webSocket.loop()` at the top of `loop()`, not from an interrupt) places the raw string into the `gcodeBuffer` at the `bufferHead` index.
Simultaneously, the main `loop()` checks if `bufferCount > 0`. If it is, and the motors aren't currently busy, it pulls the oldest string from the `bufferTail` index, parses it, and decrements the `bufferCount`. 

### The Non-Blocking `loop()`
The golden rule of the `loop()` function is that it must cycle tens of thousands of times per second. 
At the very bottom of the loop, two functions are always called:
```cpp
plateStepper.run();
armStepper.run();
```
These functions check the internal microsecond timers of the `AccelStepper` library. If it is time to pulse a motor pin, they pulse it and return immediately. If any function in the entire firmware used `delay(10)`, the motors would literally stop turning for 10 milliseconds, destroying the smoothness of the drawing.

---

## 4. G-Code Parsing Engine

G-code is the standard language of CNC machines. The `parseGcodeLine(String line)` function is responsible for digesting raw strings into mathematical targets.

### Sanitization
First, the function strips out comments. Anything following a semicolon `;` or wrapped in parentheses `()` is deleted. The string is then trimmed of whitespace and forced into `toUpperCase()` so that `g1 x10 y10` is treated identically to `G1 X10 Y10`.

### Custom Command Extensions
We extended standard G-code with custom commands specific to this architecture:
- **`M100 P<val> A<val>`**: This updates the mechanical backlash compensation deadzones for the Plate (`P`) and Arm (`A`) in real-time, allowing the user to tune the machine without recompiling C++.
- **`M101`**: Triggers a physical homing sequence. It forcefully drops the arm's acceleration profile to a safe limit, commands it to extend 4000 steps to hit the physical center limit, and zeroes out the internal coordinate system.

### Absolute vs Relative Positioning
- **`G90` (Absolute):** If the command is `G1 X10`, the target X becomes exactly `10`.
- **`G91` (Relative):** If the command is `G1 X10`, the target X becomes `current_x + 10`.

> **Known firmware limitations:** in `G91` mode, `current_x` is still the *start* of the previous move when the offset is added, so relative moves accumulate incorrectly. `G28` sets the target to the origin without updating the start point, so it does not move the pen. The Web App works around both by converting all input to absolute `G0`/`G1` moves before streaming (see Section 9).

---

## 5. Core Kinematics: Cartesian to Polar Math

The most computationally heavy part of the firmware is translating the targeted Cartesian `(X, Y)` coordinate into physical stepper pulses for the Plate (Theta) and Arm (Radius).

### The Math & Reversing Direction
```cpp
const float PLATE_STEPS_PER_REV = 13920.0;
const float STEPS_PER_MM_ARM = -3800.0 / 66.0; 

void cartesianToPolarSteps(float x_mm, float y_mm, long &outPlateSteps, long &outArmSteps) {
  float r_mm = sqrt(x_mm * x_mm + y_mm * y_mm);
  float theta = -atan2(y_mm, x_mm);
  
  outPlateSteps = round((theta / (2.0 * PI)) * PLATE_STEPS_PER_REV);
  outArmSteps = round(r_mm * STEPS_PER_MM_ARM);
}
```
**Radius (Arm):** Calculated via the Pythagorean theorem (`a² + b² = c²`). 
Notice that `STEPS_PER_MM_ARM` is intentionally **negated**. In standard math, a larger radius means positive steps. However, due to how the physical motor is mounted to the plotter, "extending" the arm moves it toward the center, and "retracting" the arm moves it away from the center. By making the conversion constant negative, we elegantly flipped the entire mathematical engine. Drawing a shape (moving away from `0,0`) now results in negative stepper pulses, physically retracting the arm correctly.

**Theta (Plate):** Calculated using the Arctangent function (`atan2`). This function returns the angle of a vector in radians. We manually negate the result (`-atan2`) to fix a physical mirroring issue; without it, all text and shapes would be drawn backward like a mirror image.

### Unwrapping the Crossover (The -180/180 Bug)
`atan2` returns values strictly between `-π` and `+π` (-180° to 180°). 
Imagine the machine is drawing a large circle, and the plate angle slowly approaches 179°. The next coordinate requires the plate to move to 181°, which `atan2` outputs as `-179°`.
If the firmware blindly commanded the motor to move to `-179°`, the plate would violently spin backwards 358 degrees just to advance a tiny fraction of an inch!
**The Fix:**
```cpp
while (theta - last_theta > PI) theta -= 2.0 * PI;
while (theta - last_theta < -PI) theta += 2.0 * PI;
```
This logic "unwraps" the angle. It checks the delta between the new angle and the last angle. If the jump is larger than 180°, it forcibly adds or subtracts a full 360°, ensuring the logical target continuously grows (e.g., `179° -> 181° -> 183°`) and the plate spins smoothly in one continuous direction.

---

## 6. Linear Interpolation Engine

A major challenge with Polar Plotters is that interpolating two points naturally results in a curved arc. If you command the arm to move to 50mm and the plate to rotate 90 degrees simultaneously, the resulting line drawn on the paper is a sweeping curve.
To draw a perfectly straight line (e.g., the edge of a square), the firmware uses **Chunking**.

```cpp
float dist = sqrt(dx * dx + dy * dy);
numChunks = max(1, (int)ceil(dist / 0.2));
```
Every straight `G1` move is mathematically chopped into microscopic `0.2mm` chunks. 
If the line is 10mm long, it is split into 50 chunks. 
The `loop()` function then executes a parametric sweep:
```cpp
float t = (float)currentChunk / numChunks;
float x_mm = current_x_mm + (target_x_mm - current_x_mm) * t;
float y_mm = current_y_mm + (target_y_mm - current_y_mm) * t;
```
As `currentChunk` increments from 0 to 50, the firmware recalculates the exact Cartesian `X,Y` coordinate along the straight line every `0.2mm`, translates it to Polar steps, and sends those steps to the motors. This forces the arm and plate to constantly accelerate and decelerate relative to each other, resulting in a perfectly straight physical toolpath.

---

## 7. Backlash Compensation Algorithm

The 28BYJ-48 stepper motors contain an internal 64:1 reduction gearbox. Like all mechanical gears, there is physical space between the teeth, known as **Backlash**. 
When a motor has been spinning clockwise and suddenly needs to spin counter-clockwise, the motor shaft must rotate several times before the gears physically touch the other side and begin turning the output shaft. Without software compensation, this results in squashed circles and disconnected lines.

### Direction Tracking & Deadzone Injection
The firmware constantly tracks `plateDir` and `armDir` (-1 or 1). 
During the Linear Interpolation chunking process, if it calculates that the next chunk requires a motor to reverse its direction, it pauses the chunking process and enters `doingBacklash = true`.
```cpp
if (newPlateDir != plateDir && nextPlateLogical != currentPlateLogical) {
  pBacklash = (newPlateDir == 1) ? PLATE_BACKLASH : -PLATE_BACKLASH;
  plateDir = newPlateDir;
}
```
The firmware injects a "Deadzone" move. It rapidly spins the reversed motor by exactly the backlash amount (e.g., 80 steps for the plate). 
Crucially, it does **not** update the logical `currentPlateLogical` variable during this move. The software is effectively moving the motor just to close the physical gap in the gears, while the logical map of the drawing remains untouched. Once the gears are tight, it resumes drawing the chunks perfectly to scale.

---

## 8. Edge Cases & Safety Protocols

### Origin Pre-Rotation (The Center Smudge)
When the pen is exactly at the physical center of the plotter `(0,0)`, the radius is zero. At a radius of zero, spinning the plate has no physical effect on the drawing.
If the firmware receives a command to draw a line starting from `(0,0)` to `(10, 10)`, the math requires the plate to be at 45 degrees. If it executes the move normally, the arm will begin extending outwards *while* the plate is rotating to 45 degrees. This causes the pen to drag across the paper in an ugly, sweeping arc originating from the center.
**The Fix:**
```cpp
if (abs(current_x_mm) < 0.1 && abs(current_y_mm) < 0.1 && dist > 0.1) {
  // Rotate the plate to the target angle while the arm remains at 0!
  plateStepper.moveTo(targetPlateSteps);
  while (plateStepper.distanceToGo() != 0) {
    plateStepper.run();
    webSocket.loop();
    yield();
  }
}
```
The firmware intercepts any move starting at `(0,0)`. It pre-calculates the final required angle, spins the plate to that angle while the pen is safely parked at dead center, and *then* begins extending the arm. This results in perfectly crisp lines radiating from the center.

---

## 9. Web App Interface

The control interface (`web/index.html`) is a standalone Single Page Application (SPA). It is built entirely in Vanilla HTML, CSS, and JavaScript. It does not require Node.js, Python, or any backend server to function. 

### Styling & UI
The design is a minimal black-and-white, monospace (Space Mono) interface with orange accents, styled with Tailwind CSS (loaded from a CDN). It is organized into:
1. **Header:** The WebSocket address, **Connect**, and **Home Arm** (disabled while streaming).
2. **Start tab:** Quick Shapes and System Tuning (live backlash settings and a calibration test).
3. **Stream tab:** File loading, the live progress bar, and a G-code preview canvas.
4. **Guide tab:** WiFi setup, calibration, and homing instructions.
5. **System console:** A log of connection events and transmitted commands.

### The JavaScript File API
When a user selects a `.gcode` file, the JS `FileReader` API loads the entire file into the browser's RAM as a single massive string. It splits this string using a Regular Expression (`text.split(/\r?\n/)`) to account for different OS line endings, and passes the lines to `normalizeGCode()`. This converts the file into the subset of G-code the firmware handles reliably:
- `G91` relative moves and `G28` are resolved into absolute `G0`/`G1` moves (see the known limitations in Section 4).
- Lines the firmware ignores (`G21`, Z-only moves, feed rates, `M3`, ...) are dropped, so they don't cost a WebSocket round-trip.
- `G1` moves shorter than 0.5mm are merged to prevent stuttering. The end point of each stroke is always kept.

The result is stored in the `gcodeLines` array. The preview draws `G1` moves in black and `G0` travel moves in orange. Because the firmware has no pen lift, travel moves are drawn on paper too.

The backlash inputs are entered in degrees and millimetres. The Web App converts them to steps using `PLATE_STEPS_PER_REV` and `ARM_STEPS_PER_MM`, which mirror the firmware constants and must be kept in sync with `firmware/src/main.cpp`.

### Quick Shapes (Trigonometry Generators)
To allow users to test the plotter without needing complex external CAD and Slicer software, the Web App features built-in mathematical generators.
Each shape is a regular polygon (or, for the star, a star polygon) generated with basic trigonometry: `cos(theta)` for X and `sin(theta)` for Y.
```javascript
function generatePolygon(sides, radius, rotation = Math.PI / 2, step = 1) {
    const gcode = ['G21', 'G90'];
    for (let i = 0; i <= sides; i++) {
        const angle = (i * step * 2 * Math.PI / sides) + rotation;
        const x = (Math.cos(angle) * radius).toFixed(2);
        const y = (Math.sin(angle) * radius).toFixed(2);
        gcode.push(`${i === 0 ? 'G0' : 'G1'} X${x} Y${y}`);
    }
    return gcode;
}
```
The first vertex is reached with a `G0` travel move from the origin. Because there is no pen lift, this travel move leaves a line from the centre to the shape.

---

## Conclusion

The Polar Plotter is a delicate balance of physical mechanical control and complex software interpolation. By utilizing non-blocking code, circular buffers, real-time chunking, sophisticated backlash deadzones, and a lightweight WebSocket ping-pong protocol, an incredibly cheap, low-power ESP8266 is capable of executing massive, high-precision CAD files flawlessly.
