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

    time.className = 't';
    time.textContent = new Date().toLocaleTimeString('en-GB', { hour12: false });

    text.className = { error: 'log-error', rx: 'log-rx', tx: 'log-tx' }[type] || '';
    text.textContent = message;

    div.append(time, text);
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function isConnected() {
    return ws && ws.readyState === WebSocket.OPEN;
}

function switchTab(targetIndex) {
    const index = parseInt(targetIndex);
    document.querySelectorAll('.pane').forEach((pane, i) => pane.classList.toggle('active', i === index));
    document.querySelectorAll('.tab-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === index);
        btn.setAttribute('aria-selected', i === index);
    });
}

function setStatus(state) {
    connStatus.dataset.state = state;
    connStatus.lastElementChild.textContent = { online: 'Connected', connecting: 'Connecting' }[state] || 'Offline';
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => switchTab(e.currentTarget.dataset.target));
});

function updateButtons() {
    btnUpdate.disabled = !isConnected();
    btnHome.disabled = !isConnected() || isStreaming;
    btnStream.disabled = !isConnected() || gcodeLines.length === 0;
    btnStream.textContent = isStreaming ? 'Pause streaming'
        : currentLineIdx > 0 ? 'Resume streaming' : 'Start streaming';
    btnStream.classList.toggle('accent', isStreaming);
    btnStream.classList.toggle('primary', !isStreaming);
}

function updateProgress() {
    const pct = gcodeLines.length ? (currentLineIdx / gcodeLines.length) * 100 : 0;
    progressFill.style.width = `${pct}%`;
    progressText.textContent = `${currentLineIdx.toLocaleString()} of ${gcodeLines.length.toLocaleString()} lines sent`;
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
   They are drawn dashed in clay to make that visible.
   ========================================================================== */

// The canvas is 500 logical px for the 125 mm plate (4 px/mm, origin at the centre),
// drawn at the screen's pixel density.
const PREVIEW_PX = 500;
const PX_PER_MM = 4.0;
const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
canvas.width = canvas.height = PREVIEW_PX * dpr;

function drawGCodePreview(lines) {
    const c = PREVIEW_PX / 2;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, PREVIEW_PX, PREVIEW_PX);
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, PREVIEW_PX, PREVIEW_PX);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // 10 mm grid
    ctx.strokeStyle = '#F0EEE6';
    ctx.lineWidth = 1;
    for (let i = c % 40; i <= PREVIEW_PX; i += 40) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, PREVIEW_PX); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(PREVIEW_PX, i); ctx.stroke();
    }

    // Axes and the Ø100 mm working circle
    ctx.strokeStyle = '#D8D5CA';
    ctx.beginPath(); ctx.moveTo(c, 0); ctx.lineTo(c, PREVIEW_PX); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, c); ctx.lineTo(PREVIEW_PX, c); ctx.stroke();
    ctx.setLineDash([3, 5]);
    ctx.beginPath(); ctx.arc(c, c, 50 * PX_PER_MM, 0, Math.PI * 2); ctx.stroke();
    ctx.setLineDash([]);

    const toPx = (mmX, mmY) => [c + mmX * PX_PER_MM, c - mmY * PX_PER_MM];
    let [px, py] = toPx(0, 0);

    // Collect strokes so draw lines sit on top of travel lines
    const draw = new Path2D();
    const travel = new Path2D();
    for (const line of lines) {
        const m = line.match(/^G([01]) X(-?[\d.]+) Y(-?[\d.]+)$/);
        if (!m) continue;
        const [nx, ny] = toPx(parseFloat(m[2]), parseFloat(m[3]));
        const path = m[1] === '0' ? travel : draw;
        path.moveTo(px, py);
        path.lineTo(nx, ny);
        [px, py] = [nx, ny];
    }

    ctx.strokeStyle = '#D97757';
    ctx.lineWidth = 1.25;
    ctx.setLineDash([4, 4]);
    ctx.stroke(travel);
    ctx.setLineDash([]);

    ctx.strokeStyle = '#141413';
    ctx.lineWidth = 1.6;
    ctx.stroke(draw);

    // Plate centre
    ctx.fillStyle = '#141413';
    ctx.beginPath(); ctx.arc(c, c, 2.5, 0, Math.PI * 2); ctx.fill();
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
    if (ws && (ws.readyState === WebSocket.CONNECTING || isConnected())) {
        ws.close();
        return;
    }

    const url = wsUrlInput.value;
    log(`Connecting to ${url}...`);
    try {
        ws = new WebSocket(url);
    } catch (err) {
        // Thrown straight away for a malformed URL, or for ws:// from an HTTPS page
        log(location.protocol === 'https:'
            ? 'This browser blocks ws:// connections from an HTTPS page. Open web/index.html from disk to connect.'
            : `Can't connect: ${err.message}`, 'error');
        return;
    }
    setStatus('connecting');
    btnConnect.textContent = 'Cancel';

    ws.onopen = () => {
        inFlight = 0;
        btnConnect.textContent = 'Disconnect';
        btnConnect.classList.replace('primary', 'quiet');
        setStatus('online');
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
        btnConnect.textContent = 'Connect';
        btnConnect.classList.replace('quiet', 'primary');
        setStatus('offline');
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

// Draw each shape's own G-code as its button icon
function shapeIcon(svg, gcode) {
    const pts = gcode
        .map(l => l.match(/X(-?[\d.]+) Y(-?[\d.]+)/))
        .filter(Boolean)
        .map(m => `${m[1]},${-parseFloat(m[2])}`);
    svg.setAttribute('viewBox', '-56 -56 112 112');
    svg.setAttribute('aria-hidden', 'true');
    svg.innerHTML = `<circle r="54"/><polyline points="${pts.join(' ')}"/>`;
}

document.querySelectorAll('.shape-btn').forEach(btn => {
    shapeIcon(btn.querySelector('svg'), SHAPES[btn.dataset.shape]());
    btn.addEventListener('click', (e) => {
        const shape = e.currentTarget.dataset.shape;
        if (!loadProgram(SHAPES[shape](), `Generated ${shape}`)) return;
        log(`Generated ${shape}.`);
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
    log('Generated calibration test.');
    switchTab(1);
});

document.getElementById('btn-how-to-cal').addEventListener('click', () => {
    switchTab(2); // Switch to Guide tab
    const section = document.getElementById('guide-calibrate');
    section.open = true;
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

document.getElementById('btn-clear').addEventListener('click', () => { terminal.textContent = ''; });

if (location.protocol === 'https:') document.getElementById('https-notice').hidden = false;

// Initialize defaults to match the firmware's boot-time backlash values
valPlate.value = (DEFAULT_PLATE_BACKLASH_STEPS * 360.0 / PLATE_STEPS_PER_REV).toFixed(2);
valArm.value = (DEFAULT_ARM_BACKLASH_STEPS / ARM_STEPS_PER_MM).toFixed(2);
drawGCodePreview([]);
updateProgress();
switchTab(0);
log('Ready. Connect to the plotter, or load a program to preview it.');
