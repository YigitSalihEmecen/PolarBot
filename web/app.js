/* ==========================================================================
   1. DOM ELEMENTS
   ========================================================================== */
const btnConnect = document.getElementById('btn-connect');
const btnUpdate = document.getElementById('btn-update');
const btnHome = document.getElementById('btn-home');
const btnStream = document.getElementById('btn-stream');
const wsUrlInput = document.getElementById('ws-url');
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const terminal = document.getElementById('terminal');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const connStatus = document.getElementById('conn-status');

const canvas = document.getElementById('gcode-canvas');
const ctx = canvas.getContext('2d');

let ws;
let gcodeLines = [];
let currentLineIdx = 0;
let isStreaming = false;

/* ==========================================================================
   2. UI CONTROLS & UTILITIES
   ========================================================================== */

function log(message, type = 'system') {
    const div = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });

    let colorClass = 'text-black';
    if (type === 'error') colorClass = 'text-red-600 font-bold';
    if (type === 'rx') colorClass = 'text-blue-600';
    if (type === 'tx') colorClass = 'text-green-600';

    div.innerHTML = `<span class="text-gray-400 mr-2">[${time}]</span><span class="${colorClass}">${message}</span>`;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function switchTab(targetIndex) {
    const slider = document.getElementById('tab-slider');
    // Each tab is 1/3 of the 300% container, so move by 33.3333% per tab
    slider.style.transform = `translateX(-${targetIndex * 33.3333}%)`;

    document.querySelectorAll('.tab-btn').forEach((btn, index) => {
        if (index === parseInt(targetIndex)) {
            btn.classList.add('font-bold', 'text-orange-500', 'border-orange-500');
            btn.classList.remove('text-gray-500', 'border-transparent');
        } else {
            btn.classList.remove('font-bold', 'text-orange-500', 'border-orange-500');
            btn.classList.add('text-gray-500', 'border-transparent');
        }
    });
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => switchTab(e.target.dataset.target));
});

/* ==========================================================================
   3. G-CODE CANVAS VISUALIZER
   ========================================================================== */
function drawGCodePreview(lines) {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background grid (10x10mm squares)
    ctx.strokeStyle = '#e5e7eb'; // gray-200
    ctx.lineWidth = 1;
    for (let i = 0; i <= 500; i += 40) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 500); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(500, i); ctx.stroke();
    }

    // Draw Axis lines
    ctx.strokeStyle = '#9ca3af'; // gray-400
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(250, 0); ctx.lineTo(250, 500); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 250); ctx.lineTo(500, 250); ctx.stroke();

    // Canvas dimensions map: 500px = 125mm. Scale = 4px/mm. Origin at (250,250).
    const scale = 4.0;
    const cx = 250;
    const cy = 250;

    let penX = 0;
    let penY = 0;
    let isPenDown = false; // Default up

    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim().toUpperCase();
        if (line.startsWith(';') || line.startsWith('(')) continue;

        let hasMoved = false;
        let newX = penX;
        let newY = penY;

        if (line.startsWith('G1')) isPenDown = true;
        if (line.startsWith('G0')) isPenDown = false;

        // Parse Z to track pen state (overrides default G0/G1)
        if (line.includes('Z')) {
            let zMatch = line.match(/Z([-\d.]+)/);
            if (zMatch) {
                let zVal = parseFloat(zMatch[1]);
                isPenDown = (zVal <= 0);
            }
        }

        // Parse X and Y
        if (line.includes('X')) {
            let xMatch = line.match(/X([-\d.]+)/);
            if (xMatch) { newX = parseFloat(xMatch[1]); hasMoved = true; }
        }
        if (line.includes('Y')) {
            let yMatch = line.match(/Y([-\d.]+)/);
            if (yMatch) { newY = parseFloat(yMatch[1]); hasMoved = true; }
        }

        if (hasMoved) {
            let plotX = cx + (newX * scale);
            let plotY = cy - (newY * scale); // Invert Y

            if (isPenDown) {
                ctx.lineTo(plotX, plotY);
            } else {
                ctx.moveTo(plotX, plotY);
            }

            penX = newX;
            penY = newY;
        }
    }

    ctx.stroke();

    // Update UI
    fileName.textContent = fileInput.files[0] ? fileInput.files[0].name : "Generated Shape";
    progressText.textContent = `0 / ${lines.length} LINES PROCESSED`;
    progressFill.style.width = '0%';

    if (ws && ws.readyState === WebSocket.OPEN) btnStream.disabled = false;
}

/* ==========================================================================
   4. WEBSOCKET LOGIC
   ========================================================================== */

btnConnect.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        return;
    }

    const url = wsUrlInput.value;
    log(`Attempting connection to ${url}...`);
    ws = new WebSocket(url);

    ws.onopen = () => {
        btnConnect.textContent = "DISCONNECT";
        btnConnect.classList.replace('bg-black', 'bg-red-500');
        btnConnect.classList.replace('hover:text-black', 'hover:text-red-500');

        connStatus.textContent = "ONLINE";
        connStatus.classList.replace('text-red-400', 'text-green-400');

        btnUpdate.disabled = false;
        btnHome.disabled = false;
        if (gcodeLines.length > 0) btnStream.disabled = false;

        log("Connection established successfully.");
    };

    ws.onmessage = (event) => {
        const msg = event.data.trim();
        if (msg !== "ok") {
            log(`ESP8266: ${msg}`, "rx");
        }

        if (msg === "ok" && isStreaming) {
            sendNextLine();
        }
    };

    ws.onerror = (error) => {
        log("WebSocket Error: Ensure plotter is powered on and connected to the same network.", "error");
    };

    ws.onclose = () => {
        btnConnect.textContent = "CONNECT";
        btnConnect.classList.replace('bg-red-500', 'bg-black');
        btnConnect.classList.replace('hover:text-red-500', 'hover:text-black');

        connStatus.textContent = "OFFLINE";
        connStatus.classList.replace('text-green-400', 'text-red-400');

        btnUpdate.disabled = true;
        btnHome.disabled = true;
        btnStream.disabled = true;
        isStreaming = false;
        log("Connection closed.");
    };
});

btnUpdate.addEventListener('click', () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const pDeg = parseFloat(document.getElementById('val-plate').value);
    const aMm = parseFloat(document.getElementById('val-arm').value);

    // Plate: 13900 steps per 360 degrees
    const pSteps = Math.round(pDeg * (13900.0 / 360.0));

    // Arm: 3500/66 steps per mm (absolute value = 53.0303)
    const aSteps = Math.round(aMm * Math.abs(3500.0 / 66.0));

    const cmd = `M100 P${pSteps} A${aSteps}`;
    ws.send(cmd);
    log(`TX: ${cmd} (Converted from ${pDeg}° and ${aMm}mm)`, "tx");
});

btnHome.addEventListener('click', () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const cmd = `M101`;
    ws.send(cmd);
    log(`TX: ${cmd} (Initiating physical homing sequence)`, "tx");
});

/* ==========================================================================
   5. STREAMING ENGINE
   ========================================================================== */

function decimateGCode(lines, thresholdMm) {
    let simplified = [];
    let lastX = 0, lastY = 0;
    let isAbsolute = true;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim().toUpperCase();

        if (line.startsWith(';') || line.startsWith('(') || line === '') continue;

        if (line.startsWith('G90')) isAbsolute = true;
        if (line.startsWith('G91')) isAbsolute = false;

        let isMove = line.startsWith('G0') || line.startsWith('G1');

        if (!isMove) {
            simplified.push(line);
            continue;
        }

        let newX = lastX, newY = lastY;
        let hasX = false, hasY = false;

        let xMatch = line.match(/X([-\d.]+)/);
        if (xMatch) {
            let val = parseFloat(xMatch[1]);
            newX = isAbsolute ? val : lastX + val;
            hasX = true;
        }

        let yMatch = line.match(/Y([-\d.]+)/);
        if (yMatch) {
            let val = parseFloat(yMatch[1]);
            newY = isAbsolute ? val : lastY + val;
            hasY = true;
        }

        let hasZ = line.includes('Z');
        let isRapid = line.startsWith('G0');

        // Always keep Z moves, G0 rapid moves, or lines without XY
        if (hasZ || isRapid || (!hasX && !hasY)) {
            simplified.push(line);
            lastX = newX;
            lastY = newY;
            continue;
        }

        let dist = Math.hypot(newX - lastX, newY - lastY);

        if (dist >= thresholdMm) {
            // Re-write line with absolute coordinates to prevent cumulative drift
            simplified.push(`G1 X${newX.toFixed(3)} Y${newY.toFixed(3)}`);
            lastX = newX;
            lastY = newY;
        }
    }

    // Always push the very last line if it was a move just to be safe
    let lastLine = lines[lines.length - 1];
    if (lastLine && (lastLine.includes('X') || lastLine.includes('Y'))) {
        simplified.push(lastLine);
    }

    return simplified;
}

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const fileReader = new FileReader();
    fileReader.onload = (event) => {
        const text = event.target.result;
        const rawLines = text.split(/\r?\n/).filter(l => l.trim() !== '');

        // Simplify G-code to prevent plotter stuttering (0.5mm resolution)
        gcodeLines = decimateGCode(rawLines, 0.5);
        currentLineIdx = 0;

        log(`Loaded file: ${file.name} (Optimized from ${rawLines.length} to ${gcodeLines.length} lines)`);
        drawGCodePreview(gcodeLines);
    };
    fileReader.readAsText(file);
});

btnStream.addEventListener('click', () => {
    if (!isStreaming) {
        if (gcodeLines.length === 0 || !ws) return;
        isStreaming = true;
        btnStream.textContent = "PAUSE STREAMING";
        btnStream.classList.replace('bg-black', 'bg-yellow-500');
        btnStream.classList.replace('hover:text-black', 'hover:text-yellow-500');
        log("Streaming initiated...");

        // Pre-fill circular buffer
        for (let i = 0; i < 4; i++) {
            sendNextLine();
        }
    } else {
        isStreaming = false;
        btnStream.textContent = "RESUME STREAMING";
        btnStream.classList.replace('bg-yellow-500', 'bg-black');
        btnStream.classList.replace('hover:text-yellow-500', 'hover:text-black');
        log("Streaming paused.");
    }
});

function sendNextLine() {
    if (!isStreaming || !ws || ws.readyState !== WebSocket.OPEN) return;

    if (currentLineIdx >= gcodeLines.length) {
        log("Streaming complete. Reached end of file.");
        isStreaming = false;
        btnStream.textContent = "START STREAMING";
        btnStream.classList.replace('bg-yellow-500', 'bg-black');
        btnStream.classList.replace('hover:text-yellow-500', 'hover:text-black');
        btnStream.disabled = true;
        return;
    }

    let line = gcodeLines[currentLineIdx].trim();
    // Skip comments and empty lines client-side for speed
    while ((line.startsWith(';') || line.startsWith('(') || line === '') && currentLineIdx < gcodeLines.length - 1) {
        currentLineIdx++;
        line = gcodeLines[currentLineIdx].trim();
    }

    ws.send(line);

    // Only log every 100th line to prevent DOM lag
    if (currentLineIdx % 100 === 0) {
        log(`TX: ${line}`, "tx");
    }

    currentLineIdx++;

    // Update Progress UI
    if (currentLineIdx % 10 === 0 || currentLineIdx === gcodeLines.length) {
        const pct = (currentLineIdx / gcodeLines.length) * 100;
        progressFill.style.width = `${pct}%`;
        progressText.textContent = `${currentLineIdx} / ${gcodeLines.length} LINES PROCESSED`;
    }
}

/* ==========================================================================
   6. QUICK SHAPE GENERATORS
   ========================================================================== */

function generatePolygon(sides, radius) {
    let gcode = ["G21", "G90", "G0 Z5"];
    for (let i = 0; i <= sides; i++) {
        let angle = (i * 2 * Math.PI / sides) + (Math.PI / 2);
        let x = (Math.cos(angle) * radius).toFixed(2);
        let y = (Math.sin(angle) * radius).toFixed(2);
        if (i === 0) {
            gcode.push(`G0 X${x} Y${y}`);
            gcode.push("G1 Z-1 F500");
        } else {
            gcode.push(`G1 X${x} Y${y}`);
        }
    }
    gcode.push("G0 Z5");
    return gcode;
}

function generateStar(radius) {
    let gcode = ["G21", "G90", "G0 Z5"];
    for (let i = 0; i <= 5; i++) {
        let angle = (i * 2 * 2 * Math.PI / 5) + (Math.PI / 2);
        let x = (Math.cos(angle) * radius).toFixed(2);
        let y = (Math.sin(angle) * radius).toFixed(2);
        if (i === 0) {
            gcode.push(`G0 X${x} Y${y}`);
            gcode.push("G1 Z-1 F500");
        } else {
            gcode.push(`G1 X${x} Y${y}`);
        }
    }
    gcode.push("G0 Z5");
    return gcode;
}

document.querySelectorAll('.shape-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const shape = e.target.dataset.shape;
        let generatedLines = [];

        if (shape === 'triangle') generatedLines = generatePolygon(3, 50);
        else if (shape === 'square') {
            let gcode = ["G21", "G90", "G0 Z5"];
            let r = 50;
            for (let i = 0; i <= 4; i++) {
                let angle = (i * 2 * Math.PI / 4) + (Math.PI / 4);
                let x = (Math.cos(angle) * r).toFixed(2);
                let y = (Math.sin(angle) * r).toFixed(2);
                if (i === 0) {
                    gcode.push(`G0 X${x} Y${y}`);
                    gcode.push("G1 Z-1 F500");
                } else gcode.push(`G1 X${x} Y${y}`);
            }
            gcode.push("G0 Z5");
            generatedLines = gcode;
        }
        else if (shape === 'pentagon') generatedLines = generatePolygon(5, 50);
        else if (shape === 'hexagon') generatedLines = generatePolygon(6, 50);
        else if (shape === 'star') generatedLines = generateStar(50);

        gcodeLines = generatedLines;
        currentLineIdx = 0;
        log(`Successfully generated ${shape}.`);

        // Automatically switch to Stream tab (index 1) and preview the shape!
        switchTab(1);
        drawGCodePreview(gcodeLines);
    });
});

document.getElementById('btn-calibration').addEventListener('click', () => {
    let gcode = ["G21", "G90", "G0 Z5"];

    // 40x40 Square Centered
    gcode.push("G0 X-20 Y-20");
    gcode.push("G1 Z-1 F500");
    gcode.push("G1 X20 Y-20");
    gcode.push("G1 X20 Y20");
    gcode.push("G1 X-20 Y20");
    gcode.push("G1 X-20 Y-20");
    gcode.push("G0 Z5");

    // Crosshair
    gcode.push("G0 X-20 Y0");
    gcode.push("G1 Z-1 F500");
    gcode.push("G1 X20 Y0");
    gcode.push("G0 Z5");

    gcode.push("G0 X0 Y-20");
    gcode.push("G1 Z-1 F500");
    gcode.push("G1 X0 Y20");
    gcode.push("G0 Z5");

    gcodeLines = gcode;
    currentLineIdx = 0;
    log(`Successfully generated Calibration Test Shape.`);

    switchTab(1);
    drawGCodePreview(gcodeLines);
});

document.getElementById('btn-how-to-cal').addEventListener('click', () => {
    switchTab(2); // Switch to Guide tab
    document.getElementById('guide-calibrate').open = true;
});

// Initialize defaults
drawGCodePreview(["G0 X0 Y0"]); // Draw empty grid
switchTab(0);
log("Web App initialized. Ready to connect.");
