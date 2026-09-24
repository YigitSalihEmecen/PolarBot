/* ==========================================================================
   1. CONSTANTS & DOM ELEMENTS
   ========================================================================== */

// Mirror of the hardware constants in firmware/src/main.cpp — keep in sync.
const PLATE_STEPS_PER_REV = 13920.0;
const ARM_STEPS_PER_MM = 3800.0 / 66.0;
const DEFAULT_PLATE_BACKLASH_STEPS = 80;
const DEFAULT_ARM_BACKLASH_STEPS = 100;

// The firmware ring buffer holds 8 lines; keep at most 4 in flight.
const MAX_IN_FLIGHT = 4;

// Moves shorter than this are merged to prevent stuttering on dense files.
const DECIMATE_MM = 0.5;

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
const valPlate = document.getElementById('val-plate');
const valArm = document.getElementById('val-arm');

const canvas = document.getElementById('gcode-canvas');
const ctx = canvas.getContext('2d');

let ws;
let gcodeLines = [];
let currentLineIdx = 0;
let inFlight = 0;
let isStreaming = false;

/* ==========================================================================
   2. UI CONTROLS & UTILITIES
   ========================================================================== */

function log(message, type = 'system') {
    const div = document.createElement('div');
    const time = document.createElement('span');
    const text = document.createElement('span');

    time.className = 'text-gray-400 mr-2';
    time.textContent = `[${new Date().toLocaleTimeString('en-US', { hour12: false })}]`;

    text.className = {
        error: 'text-red-600 font-bold',
        rx: 'text-blue-600',
        tx: 'text-green-600',
    }[type] || 'text-black';
    text.textContent = message;

    div.append(time, text);
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function isConnected() {
    return ws && ws.readyState === WebSocket.OPEN;
}

function switchTab(targetIndex) {
    const slider = document.getElementById('tab-slider');
    // Each tab is 1/3 of the 300% container, so move by 33.3333% per tab
    slider.style.transform = `translateX(-${targetIndex * 33.3333}%)`;

    document.querySelectorAll('.tab-btn').forEach((btn, index) => {
        const active = index === parseInt(targetIndex);
        btn.classList.toggle('font-bold', active);
        btn.classList.toggle('text-orange-500', active);
        btn.classList.toggle('border-orange-500', active);
        btn.classList.toggle('text-gray-500', !active);
        btn.classList.toggle('border-transparent', !active);
    });
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => switchTab(e.currentTarget.dataset.target));
});

function updateButtons() {
    btnUpdate.disabled = !isConnected();
    btnHome.disabled = !isConnected() || isStreaming;
    btnStream.disabled = !isConnected() || gcodeLines.length === 0;
    btnStream.textContent = isStreaming ? 'PAUSE STREAMING'
        : currentLineIdx > 0 ? 'RESUME STREAMING' : 'START STREAMING';
    btnStream.classList.toggle('bg-yellow-500', isStreaming);
    btnStream.classList.toggle('bg-black', !isStreaming);
}

function updateProgress() {
    const pct = gcodeLines.length ? (currentLineIdx / gcodeLines.length) * 100 : 0;
    progressFill.style.width = `${pct}%`;
    progressText.textContent = `${currentLineIdx} / ${gcodeLines.length} LINES SENT`;
}

/* ==========================================================================
   3. G-CODE NORMALIZATION
   Converts any input into the subset the firmware handles reliably:
   absolute "G0/G1 X Y" moves plus the custom M100/M101 commands.
   - G91 relative moves are resolved to absolute coordinates.
   - G28 becomes an explicit move to the origin.
   - Lines the firmware ignores (G21, Z-only, F, M3, ...) are dropped.
   - G1 moves shorter than DECIMATE_MM are merged; stroke ends are kept.
   ========================================================================== */

function normalizeGCode(rawLines) {
    const out = ['G90'];
    let x = 0, y = 0;          // true position after each input line
    let sentX = 0, sentY = 0;  // last position actually emitted
    let absolute = true;

    const emit = (cmd, ex, ey) => {
        out.push(`${cmd} X${ex.toFixed(3)} Y${ey.toFixed(3)}`);
        sentX = ex;
        sentY = ey;
    };
    const flush = () => {
        if (x !== sentX || y !== sentY) emit('G1', x, y);
    };

    for (const raw of rawLines) {
        // Same comment handling as the firmware: cut at '(' or ';'
        const line = raw.split(/[(;]/)[0].trim().toUpperCase();
        if (!line) continue;

        if (/M10[01](?!\d)/.test(line)) { flush(); out.push(line); continue; }
        if (line.includes('G90')) { absolute = true; continue; }
        if (line.includes('G91')) { absolute = false; continue; }
        if (line.includes('G28')) { flush(); x = 0; y = 0; emit('G0', 0, 0); continue; }

        const isRapid = /G0?0(?!\d)/.test(line);
        if (!isRapid && !/G0?1(?!\d)/.test(line)) continue;

        const mx = line.match(/X(-?[\d.]+)/);
        const my = line.match(/Y(-?[\d.]+)/);
        if (!mx && !my) continue;

        // Close the current stroke at its true end before travelling
        if (isRapid) flush();

        if (mx) x = absolute ? parseFloat(mx[1]) : x + parseFloat(mx[1]);
        if (my) y = absolute ? parseFloat(my[1]) : y + parseFloat(my[1]);

        if (isRapid) emit('G0', x, y);
        else if (Math.hypot(x - sentX, y - sentY) >= DECIMATE_MM) emit('G1', x, y);
    }
    flush();
    return out;
}

/* ==========================================================================
   4. G-CODE CANVAS VISUALIZER
   The firmware has no pen lift, so G0 travel moves are drawn on paper too.
   They are shown in orange to make that visible.
   ========================================================================== */

function drawGCodePreview(lines) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background grid (10x10mm squares)
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 500; i += 40) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 500); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(500, i); ctx.stroke();
    }

    // Axis lines
    ctx.strokeStyle = '#9ca3af';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(250, 0); ctx.lineTo(250, 500); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 250); ctx.lineTo(500, 250); ctx.stroke();

    // Canvas dimensions map: 500px = 125mm. Scale = 4px/mm. Origin at (250,250).
    const scale = 4.0;
    const toPx = (mmX, mmY) => [250 + mmX * scale, 250 - mmY * scale];

    ctx.lineWidth = 1.5;
    let [px, py] = toPx(0, 0);

    for (const line of lines) {
        const m = line.match(/^G([01]) X(-?[\d.]+) Y(-?[\d.]+)$/);
        if (!m) continue;
        const [nx, ny] = toPx(parseFloat(m[2]), parseFloat(m[3]));

        ctx.strokeStyle = m[1] === '0' ? '#fdba74' : '#000000';
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(nx, ny); ctx.stroke();
        [px, py] = [nx, ny];
    }
}

function loadProgram(rawLines, name) {
    if (isStreaming) {
        log('Pause streaming before loading a new program.', 'error');
        return false;
    }
    gcodeLines = normalizeGCode(rawLines);
    currentLineIdx = 0;
    fileName.textContent = name;
    drawGCodePreview(gcodeLines);
    updateProgress();
    updateButtons();
    return true;
}

/* ==========================================================================
   5. WEBSOCKET LOGIC
   ========================================================================== */

function send(cmd) {
    ws.send(cmd);
    inFlight++;
}

btnConnect.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.CONNECTING) return;
    if (isConnected()) {
        ws.close();
        return;
    }

    const url = wsUrlInput.value;
    log(`Attempting connection to ${url}...`);
    ws = new WebSocket(url);

    ws.onopen = () => {
        inFlight = 0;
        btnConnect.textContent = 'DISCONNECT';
        btnConnect.classList.replace('bg-black', 'bg-red-500');
        connStatus.textContent = 'ONLINE';
        connStatus.classList.replace('text-orange-500', 'text-green-400');
        updateButtons();
        log('Connection established successfully.');
    };

    ws.onmessage = (event) => {
        const msg = event.data.trim();
        if (msg === 'ok') {
            // Firmware sends "ok" each time it pulls a line from its buffer
            inFlight = Math.max(0, inFlight - 1);
            pump();
        } else {
            log(`ESP8266: ${msg}`, 'rx');
        }
    };

    ws.onerror = () => {
        log('WebSocket Error: Ensure plotter is powered on and connected to the same network.', 'error');
    };

    ws.onclose = () => {
        btnConnect.textContent = 'CONNECT';
        btnConnect.classList.replace('bg-red-500', 'bg-black');
        connStatus.textContent = 'OFFLINE';
        connStatus.classList.replace('text-green-400', 'text-orange-500');
        if (isStreaming) log('Streaming interrupted.', 'error');
        isStreaming = false;
        inFlight = 0;
        updateButtons();
        log('Connection closed.');
    };
});

btnUpdate.addEventListener('click', () => {
    if (!isConnected()) return;

    const pDeg = parseFloat(valPlate.value);
    const aMm = parseFloat(valArm.value);
    if (!(pDeg >= 0) || !(aMm >= 0)) {
        log('Backlash values must be non-negative numbers.', 'error');
        return;
    }

    const pSteps = Math.round(pDeg * (PLATE_STEPS_PER_REV / 360.0));
    const aSteps = Math.round(aMm * ARM_STEPS_PER_MM);

    const cmd = `M100 P${pSteps} A${aSteps}`;
    send(cmd);
    log(`TX: ${cmd} (Converted from ${pDeg}° and ${aMm}mm)`, 'tx');
});

btnHome.addEventListener('click', () => {
    if (!isConnected() || isStreaming) return;
    send('M101');
    log('TX: M101 (Initiating physical homing sequence)', 'tx');
});

/* ==========================================================================
   6. STREAMING ENGINE
   ========================================================================== */

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    fileInput.value = ''; // allow re-loading the same file
    if (!file) return;

    const fileReader = new FileReader();
    fileReader.onload = (event) => {
        const rawLines = event.target.result.split(/\r?\n/);
        if (loadProgram(rawLines, file.name)) {
            log(`Loaded file: ${file.name} (${rawLines.length} lines → ${gcodeLines.length} after optimization)`);
        }
    };
    fileReader.readAsText(file);
});

btnStream.addEventListener('click', () => {
    if (gcodeLines.length === 0 || !isConnected()) return;
    isStreaming = !isStreaming;
    log(isStreaming ? 'Streaming started...' : 'Streaming paused.');
    updateButtons();
    pump();
});

// Keep up to MAX_IN_FLIGHT lines queued on the plotter.
function pump() {
    while (isStreaming && isConnected() && inFlight < MAX_IN_FLIGHT && currentLineIdx < gcodeLines.length) {
        const line = gcodeLines[currentLineIdx];
        send(line);
        // Only log every 100th line to prevent DOM lag
        if (currentLineIdx % 100 === 0) log(`TX: ${line}`, 'tx');
        currentLineIdx++;
    }
    updateProgress();

    if (isStreaming && currentLineIdx >= gcodeLines.length) {
        isStreaming = false;
        currentLineIdx = 0;
        log('All lines sent. The plotter finishes the last buffered moves on its own.');
        updateButtons();
    }
}

/* ==========================================================================
   7. QUICK SHAPE GENERATORS
   ========================================================================== */

// Regular polygon (step=1) or star polygon (step=2) inscribed in a circle.
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

const SHAPES = {
    triangle: () => generatePolygon(3, 50),
    square: () => generatePolygon(4, 50, Math.PI / 4),
    pentagon: () => generatePolygon(5, 50),
    hexagon: () => generatePolygon(6, 50),
    star: () => generatePolygon(5, 50, Math.PI / 2, 2),
};

document.querySelectorAll('.shape-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const shape = e.currentTarget.dataset.shape;
        if (!loadProgram(SHAPES[shape](), `Generated ${shape}`)) return;
        log(`Successfully generated ${shape}.`);
        switchTab(1);
    });
});

document.getElementById('btn-calibration').addEventListener('click', () => {
    const gcode = [
        'G21', 'G90',
        // 40x40 square centered
        'G0 X-20 Y-20', 'G1 X20 Y-20', 'G1 X20 Y20', 'G1 X-20 Y20', 'G1 X-20 Y-20',
        // Crosshair
        'G0 X-20 Y0', 'G1 X20 Y0',
        'G0 X0 Y-20', 'G1 X0 Y20',
    ];
    if (!loadProgram(gcode, 'Calibration test')) return;
    log('Successfully generated Calibration Test Shape.');
    switchTab(1);
});

document.getElementById('btn-how-to-cal').addEventListener('click', () => {
    switchTab(2); // Switch to Guide tab
    document.getElementById('guide-calibrate').open = true;
});

// Initialize defaults to match the firmware's boot-time backlash values
valPlate.value = (DEFAULT_PLATE_BACKLASH_STEPS * 360.0 / PLATE_STEPS_PER_REV).toFixed(2);
valArm.value = (DEFAULT_ARM_BACKLASH_STEPS / ARM_STEPS_PER_MM).toFixed(2);
drawGCodePreview([]);
updateProgress();
switchTab(0);
log('Web App initialized. Ready to connect.');
