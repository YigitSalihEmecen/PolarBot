# PolarBot

A low-cost, WiFi-controlled **polar plotter**. It draws on a rotating build plate using two 28BYJ-48 stepper motors and an ESP8266. You can stream G-code to it from a browser.

Most plotters move a pen along X and Y. PolarBot rotates the paper (θ) and moves the pen along a linear arm (r). The firmware converts Cartesian G-code into polar motion in real time.

![Platform](https://img.shields.io/badge/platform-ESP8266-blue)
![Framework](https://img.shields.io/badge/framework-Arduino%20%2F%20PlatformIO-orange)
![Web](https://img.shields.io/badge/web%20app-vanilla%20JS-yellow)

---

## Features

- **Cartesian → polar kinematics.** Standard `G0`/`G1` moves are converted to plate and arm steps, with angle unwrapping so the plate never spins the long way round.
- **Straight lines.** Each move is split into 0.2 mm segments, so straight lines stay straight instead of curving into arcs.
- **Backlash compensation.** Direction reversals add a gap-closing move for each axis. You can tune it live over WiFi without reflashing.
- **Wireless streaming.** G-code is sent over a WebSocket with an `ok`-based handshake, so the ESP8266's small buffer never overflows.
- **No IP lookup needed.** WiFiManager provides a setup portal for your WiFi, and mDNS makes the plotter reachable at `polarplotter.local`.
- **Browser control panel.** A single static page with a G-code preview, progress bar, built-in test shapes, calibration and a console. It needs no build step and no server.

## Repository structure

```
PolarBot/
├── firmware/      ESP8266 firmware (PlatformIO project)
│   ├── platformio.ini
│   └── src/main.cpp
├── web/           Browser control panel (open index.html)
├── cad/           3D-printable parts (STL)
└── docs/          In-depth architecture & design notes
```

## How it works

```mermaid
flowchart LR
    A[".gcode file"] --> B["Web app<br/>(browser)"]
    B -- "WebSocket :81<br/>one line per 'ok'" --> C["ESP8266<br/>8-line ring buffer"]
    C --> D["G-code parser"]
    D --> E["0.2 mm segmentation<br/>+ XY → r, θ"]
    E --> F["Backlash<br/>compensation"]
    F --> G["Plate stepper (θ)"]
    F --> H["Arm stepper (r)"]
```

For a full walkthrough of the firmware, kinematics, buffering and the hardware issues solved along the way, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Hardware

### Bill of materials

| Qty | Part | Notes |
|:---:|------|-------|
| 1 | NodeMCU v2 (ESP8266) | Microcontroller + WiFi |
| 2 | 28BYJ-48 stepper motor (5 V) | One rotates the plate, one drives the arm |
| 2 | ULN2003 driver board | One per motor |
| 1 | 5 V power supply | Must supply both motors and the WiFi current spikes |
| 1 | Pen | Held by the printed pen holder |
| — | Printed parts | See [`cad/`](cad) |

### Printed parts

| File | Description |
|------|-------------|
| `base_plate.stl` | Main machine base that the motors and rail mount on |
| `build_plate.stl` | Rotating Ø150 mm plate that carries the paper |
| `paper_clamp.stl` | Thin ring that holds the paper on the build plate |
| `base_gear.stl` | Gear that drives the build plate |
| `linear_rail.stl` | Linear rail for the pen arm |
| `linear_cap.stl` | Cap that closes the linear rail assembly |
| `linear_gear.stl` | Gear that drives the pen arm along the rail |
| `linear_stabilizer_gear.stl` | Idler gear that keeps the arm stable on the rail |
| `pen_holder_body.stl` | Pen holder body |
| `pen_holder_cap.stl` | Pen holder cap |

### Wiring

Both motors use AccelStepper in `HALF4WIRE` mode (4096 steps/rev). The pins below are GPIO numbers, listed in the order they are passed to the `AccelStepper` constructor.

| Motor | GPIO (NodeMCU label) |
|-------|----------------------|
| Plate (θ) | 5 (D1), 14 (D5), 4 (D2), 12 (D6) |
| Arm (r) | 13 (D7), 16 (D0), 3 (RX), 1 (TX) |

> [!NOTE]
> The arm motor uses the TX/RX pins, so the firmware does **not** use `Serial`. All communication goes over WiFi. Disconnect the arm driver when flashing over USB if the upload fails.

---

## Getting started

### 1. Flash the firmware

Install [PlatformIO](https://platformio.org/) (CLI or the VS Code extension), then:

```bash
cd firmware
pio run --target upload
```

Library dependencies (AccelStepper, WebSockets, WiFiManager) are installed automatically.

### 2. Connect to WiFi

On first boot, the arm homes itself. The board then opens a WiFi access point called **`PolarPlotter-Setup`**:

1. Connect to it from a phone or laptop. A setup portal should open; if it doesn't, go to `http://192.168.4.1`.
2. Pick your home network and enter the password.
3. The board saves the credentials and joins your network on every boot from then on.

### 3. Open the control panel

Open [`web/index.html`](web/index.html) in a browser on the same network and click **CONNECT**. The default address is `ws://polarplotter.local:81`. If mDNS doesn't resolve on your network, replace the hostname with the board's IP address.

### 4. Plot

1. Put the pen at the centre of the plate, or click **HOME ARM**.
2. Try a **Quick Shape**, or load a `.gcode` file in the **STREAM** tab.
3. Check the preview (125 mm diameter) and click **START STREAMING**.

---

## G-code support

| Command | Meaning |
|---------|---------|
| `G0` / `G1 X Y` | Move to X, Y in mm (origin = plate centre) |
| `G90` / `G91` | Absolute / relative positioning |
| `G28` | Return to origin |
| `M100 P<steps> A<steps>` | Set plate / arm backlash compensation (custom) |
| `M101` | Home the arm (custom) |

`Z` values and feed rates are ignored. The firmware has no pen-lift axis.

The web app removes moves shorter than 0.5 mm before streaming. This keeps dense files (for example SVG exports) from stuttering.

## Calibration

The motors' internal gearboxes have backlash. To compensate:

1. Click **DRAW CALIBRATION TEST** in the Start tab. It draws a 40 × 40 mm square with a crosshair.
2. Measure the square. Enter the shortfall as **ARM BACKLASH (MM)**.
3. If the crosshair or the corners are misaligned, adjust **PLATE BACKLASH (DEGREES)** in steps of about 0.5°.
4. Click **UPDATE Live Settings** and repeat until the square is accurate.

Steps-per-revolution and steps-per-mm are constants at the top of [`firmware/src/main.cpp`](firmware/src/main.cpp) (`PLATE_STEPS_PER_REV`, `STEPS_PER_MM_ARM`).
