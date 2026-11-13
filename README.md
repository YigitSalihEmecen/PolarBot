<p align="center">
  <img src="assets/banner.svg" alt="PolarBot: a Wi-Fi polar plotter that draws on a spinning plate" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCU-ESP8266-141413?style=flat-square&labelColor=F0EEE6" alt="ESP8266" />
  <img src="https://img.shields.io/badge/build-PlatformIO-141413?style=flat-square&labelColor=F0EEE6" alt="PlatformIO" />
  <img src="https://img.shields.io/badge/web%20app-vanilla%20JS-141413?style=flat-square&labelColor=F0EEE6" alt="Vanilla JS web app" />
  <img src="https://img.shields.io/badge/power-one%20USB%20cable-D97757?style=flat-square&labelColor=F0EEE6" alt="Powered by one USB cable" />
  <img src="https://img.shields.io/badge/license-MIT-141413?style=flat-square&labelColor=F0EEE6" alt="MIT license" />
</p>

<p align="center">
  <a href="#hardware">Hardware</a> ·
  <a href="#build-guide">Build guide</a> ·
  <a href="#getting-started">Getting started</a> ·
  <a href="#g-code-support">G-code</a> ·
  <a href="#calibration">Calibration</a> ·
  <a href="#how-it-works">How it works</a>
</p>

---

**PolarBot** is a low-cost, Wi-Fi-controlled **polar plotter**. It draws on a rotating build plate using two 28BYJ-48 stepper motors and an ESP8266, and you stream G-code to it from a browser.

Most plotters move a pen along X and Y. PolarBot rotates the paper (θ) and moves the pen along a linear arm (r). The firmware converts Cartesian G-code into polar motion in real time.

<p align="center">
  <img src="images/hero.jpg" alt="PolarBot on a desk" width="32%" />
  <img src="assets/renders/render-hero.png" alt="PolarBot render with a plotted rose" width="34%" />
  <img src="images/top.jpg" alt="PolarBot from above" width="31%" />
</p>

## Highlights

|  |  |
|---|---|
| **Cartesian → polar kinematics** | `G0`/`G1` moves become plate and arm steps. Angle unwrapping means the plate never spins the long way round. |
| **Straight lines** | Each move is split into 0.2 mm segments, so straight lines stay straight instead of curving into arcs. |
| **Backlash compensation** | Direction reversals add a gap-closing move for each axis. You can tune it over Wi-Fi without reflashing. |
| **Wireless streaming** | G-code goes over a WebSocket with an `ok`-based handshake, so the ESP8266's small buffer never overflows. |
| **No IP lookup** | WiFiManager provides a setup portal, and mDNS makes the plotter reachable at `polarplotter.local`. |
| **Browser control panel** | One static page with a G-code preview, a progress bar, test shapes, calibration and a console. No build step, no server. |
| **One cable** | Both motor drivers run from the NodeMCU's 5 V pin, so a single USB port powers the whole machine. |

---

# Hardware

<p align="center">
  <img src="assets/exploded.svg" alt="Exploded view" width="100%" />
</p>

The machine is two mechanisms in one base:

* **θ: the plate.** A 28BYJ-48 under the plate turns a 20-tooth pinion. The pinion drives a 68-tooth ring gear moulded into the underside of the build plate, which spins on a 6808 bearing on the centre hub. That's 4096 × 68⁄20 ≈ 13 920 steps per turn: the `PLATE_STEPS_PER_REV` constant in the firmware.
* **r: the arm.** A second 28BYJ-48 in the lobe drives a printed rack. The rack slides under the lobe cap, and its ring end carries a spring-loaded pen holder over the plate.

The paper is held flat by a clamp ring. Six magnets in the clamp pull against six in the plate.

<details>
<summary><b>Technical drawing</b>: dimensions and hidden components</summary>
<br/>
<p align="center">
  <img src="assets/blueprint.svg" alt="Orthographic drawing with hidden components" width="100%" />
</p>
</details>

## Components

<p align="center">
  <img src="assets/components.svg" alt="Bill of materials" width="100%" />
</p>

| Qty | Part | Notes |
|:---:|------|-------|
| 1 | **NodeMCU v2** (ESP8266) | Microcontroller and Wi-Fi. Its micro-USB port faces the hole in the lobe's end |
| 2 | **28BYJ-48 stepper motor** (5 V) | One turns the plate, one drives the arm |
| 2 | **ULN2003 driver board** | One per motor, powered from the NodeMCU |
| 1 | **6808-2RS ball bearing** | 40 × 52 × 7 mm. Pressed into the build plate, sits on the centre hub |
| 12 | **Disc magnet Ø5 × 1.5 mm** | Six in the build plate, six in the paper clamp |
| 1 | **Ø3 mm pen refill** | Metal ballpoint refill, held by the printed pen holder |
| 1 | **USB cable** | The only power source for the whole machine |
| – | M3 screws, jumper wires | For the drivers, motors and lobe cap |

## Printed parts

<p align="center">
  <img src="assets/printed-parts.svg" alt="Printed parts" width="100%" />
</p>

All models are in [`cad/`](cad). They are exported in their assembled positions, so they line up when you load them into one scene.

| File | Part | Colour in the photos |
|------|------|--------|
| `base_plate.stl` | Base: holds the hub, both motors, both drivers and the NodeMCU | Orange |
| `build_plate.stl` | Rotating Ø150 mm plate, with a 68-tooth ring gear underneath | White |
| `paper_clamp.stl` | Thin magnetic ring that holds the paper on the plate | Black |
| `base_gear.stl` | 20-tooth pinion for the plate motor | White |
| `linear_gear.stl` | 20-tooth pinion for the arm motor | White |
| `linear_rail.stl` | Rack arm with the pen ring | Black |
| `linear_cap.stl` | Lobe cap; its rib guides the rack | White |
| `pen_holder_body.stl` | Spring-loaded pen holder, screws into the rack ring | Black |
| `pen_holder_cap.stl` | Pen holder cap | Black |

## Wiring

<p align="center">
  <img src="assets/wiring.svg" alt="Wiring diagram: NodeMCU pins D1, D2, D5, D6 to the plate ULN2003 driver; D7, RX, D0, TX to the arm driver; VIN and GND power both drivers; each driver connects to a 28BYJ-48 motor" width="100%" />
</p>

| Driver input | Plate (θ) | Arm (r) |
|:------------:|:---------:|:-------:|
| IN1 | D1 · GPIO5 | D7 · GPIO13 |
| IN2 | D2 · GPIO4 | RX · GPIO3 |
| IN3 | D5 · GPIO14 | D0 · GPIO16 |
| IN4 | D6 · GPIO12 | TX · GPIO1 |
| − / + | GND / VIN | GND / VIN |

Both motors run in AccelStepper `HALF4WIRE` mode (4096 steps/rev). In the firmware, pins are passed in the order `IN1, IN3, IN2, IN4`, which is the correct coil sequence for the 28BYJ-48.

> [!NOTE]
> **Power:** both ULN2003 boards take their 5 V and GND straight from the NodeMCU, so the whole machine runs from a single USB port. The firmware homes the arm *before* turning on Wi-Fi, so the motors and the radio never draw peak current at the same time.

> [!NOTE]
> The arm motor uses the TX/RX pins, so the firmware does **not** use `Serial`. All communication goes over Wi-Fi. If a USB upload fails, disconnect the arm driver while flashing.

---

# Build guide

| | |
|:---:|:---:|
| <img src="assets/steps/step-1.svg" alt="Step 1" /> | <img src="assets/steps/step-2.svg" alt="Step 2" /> |
| **1** Seat the NodeMCU in the lobe, USB port facing the end hole. Screw both ULN2003 boards onto their standoffs. | **2** Screw the plate motor into its cradle and the arm motor into the lobe. Press a pinion onto each shaft. |
| <img src="assets/steps/step-3.svg" alt="Step 3" /> | <img src="assets/steps/step-4.svg" alt="Step 4" /> |
| **3** Wire everything as in the [wiring diagram](#wiring). | **4** Press the 6808 bearing into the plate and glue a magnet into each pocket. Drop the plate onto the hub so its ring gear meshes with the pinion. |
| <img src="assets/steps/step-5.svg" alt="Step 5" /> | <img src="assets/steps/step-6.svg" alt="Step 6" /> |
| **5** Slide the rack arm in through the lobe, teeth against the pinion. Screw the lobe cap on. | **6** Screw the pen holder into the ring, drop in the refill and close the holder cap. |
| <img src="assets/steps/step-7.svg" alt="Step 7" /> | <img src="assets/renders/render-inside.png" alt="Inside the base" /> |
| **7** Lay a paper disc on the plate and snap the magnetic clamp on top. | Inside the base, without the plate. |

<details>
<summary><b>Build photos</b></summary>
<br/>
<p align="center">
  <img src="images/parts.jpg" alt="All parts laid out: plate, base with electronics, lobe cap, pen holder and clamp" width="100%" />
</p>
<p align="center">
  <img src="images/inside.jpg" alt="Inside the base: both ULN2003 drivers, the plate motor with its pinion, the bearing hub and the rack" width="49%" />
  <img src="images/plate-gear.jpg" alt="Underside of the build plate: ring gear and 6808 bearing" width="49%" />
</p>
<p align="center">
  <img src="images/pen-holder.jpg" alt="Spring-loaded pen holder with refill" width="32%" />
  <img src="images/clamp.jpg" alt="Lifting the magnetic paper clamp" width="32%" />
  <img src="images/upright.jpg" alt="PolarBot held upright" width="32%" />
</p>
</details>

---

# Software

## Getting started

### 1. Flash the firmware

Install [PlatformIO](https://platformio.org/) (CLI or the VS Code extension), then:

```bash
cd firmware
pio run --target upload
```

PlatformIO installs the libraries (AccelStepper, WebSockets, WiFiManager) automatically.

### 2. Connect to Wi-Fi

On first boot the arm homes itself. The board then opens a Wi-Fi access point called **`PolarPlotter-Setup`**:

1. Connect to it from a phone or laptop. A setup portal should open; if it doesn't, go to `http://192.168.4.1`.
2. Pick your home network and enter the password.
3. The board saves the credentials and joins that network on every boot.

### 3. Open the control panel

Open [`web/index.html`](web/index.html) in a browser on the same network and click **Connect**. The default address is `ws://polarplotter.local:81`. If mDNS doesn't resolve on your network, replace the hostname with the board's IP address.

A hosted copy runs at **[yigitsalihemecen.github.io/PolarBot](https://yigitsalihemecen.github.io/PolarBot/)**. It previews G-code and test shapes but can't drive the plotter (see [Limitations](#limitations)).

### 4. Plot

1. Put the pen at the centre of the plate, or click **Home arm**.
2. Try a **Quick shape**, or load a `.gcode` file in the **Stream** tab.
3. Check the preview (125 mm diameter) and click **Start streaming**.

## G-code support

| Command | Meaning |
|---------|---------|
| `G0` / `G1 X Y` | Move to X, Y in mm (origin = plate centre) |
| `G90` / `G91` | Absolute / relative positioning |
| `G28` | Return to origin |
| `M100 P<steps> A<steps>` | Set plate / arm backlash compensation (custom) |
| `M101` | Home the arm (custom) |

`Z` values and feed rates are ignored. The firmware has no pen-lift axis, so the pen stays down during `G0` travel moves too. The preview shows these travel moves as dashed orange lines.

Before streaming, the web app converts every file to absolute `G0`/`G1` moves: it resolves `G91` relative moves and `G28`, and drops lines the firmware would ignore. It also merges moves shorter than 0.5 mm, which keeps dense files such as SVG exports from stuttering.

## Calibration

The motors' internal gearboxes have backlash. To compensate:

1. Click **Draw calibration test** in the Start tab. It draws a 40 × 40 mm square with a crosshair.
2. Measure the square. Enter the shortfall as the **Arm** backlash (mm).
3. If the crosshair or the corners are misaligned, adjust the **Plate** backlash (degrees) in steps of about 0.5°.
4. Click **Send to plotter** and repeat until the square is accurate.

Steps-per-revolution and steps-per-mm are constants at the top of [`firmware/src/main.cpp`](firmware/src/main.cpp) (`PLATE_STEPS_PER_REV`, `STEPS_PER_MM_ARM`).

## How it works

<p align="center">
  <img src="docs/images/architecture.svg" alt="PolarBot architecture: web app streams G-code over WebSocket to the ESP8266, which buffers, converts to polar coordinates, compensates backlash and drives the plate and arm motors" width="100%">
</p>

For a full walkthrough of the firmware, kinematics, buffering and the hardware issues solved along the way, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Limitations

- **No pen lift.** The pen touches the paper at all times, so every `G0` travel move leaves a line. Designs work best as one continuous path, or as strokes that start and end near each other.
- **Open-loop homing.** There is no endstop. Homing drives the arm into its mechanical stop for a fixed time and treats that as the centre. Accuracy depends on the pen being mounted consistently.
- **Backlash resets on reboot.** Values set with `M100` are not saved. The firmware starts with its built-in defaults every time it powers on.
- **Firmware `G91` / `G28` handling.** The firmware applies relative moves incorrectly, and `G28` doesn't move the pen. The web app converts these to absolute moves, so this only matters if you send G-code another way.
- **Web app runs locally.** Browsers block unencrypted WebSocket connections from HTTPS pages, so the [hosted copy](https://yigitsalihemecen.github.io/PolarBot/) on GitHub Pages can only preview. To plot, open `web/index.html` from disk.
- **No position feedback.** The 28BYJ-48 motors can skip steps under load without the firmware noticing.

## Roadmap

- [ ] Servo-driven pen lift (`M3`/`M5` or `Z` moves)
- [ ] Fix `G91` relative moves and `G28` in the firmware
- [ ] Save backlash settings to flash
- [ ] Serve the web app from the ESP8266 itself (`http://polarplotter.local`)
- [ ] Endstop or hall sensor for repeatable homing
- [ ] Built-in SVG → G-code conversion in the web app

---

## Repository structure

```
PolarBot/
├── cad/           3D-printable parts (STL, assembled positions)
├── firmware/      ESP8266 firmware (PlatformIO project)
│   ├── platformio.ini
│   └── src/main.cpp
├── web/           Browser control panel (open index.html)
├── docs/          Architecture notes and diagrams
├── assets/        README visuals (SVG and renders)
├── images/        Photos of the build
├── tools/render/  Python scripts that generate the visuals from the STLs
└── LICENSE
```

<details>
<summary><b>Regenerating the visuals</b></summary>
<br/>

The exploded view, build guide, technical drawing and renders are not hand-drawn. `tools/render` builds them from the STLs in `cad/` with a small NumPy rasteriser and a hidden-line extractor. The off-the-shelf parts (NodeMCU, motors, drivers, bearing, magnets, refill) are modelled as simple solids, placed on the base's real mounting features. After changing a part, run:

```bash
pip install numpy scipy matplotlib pillow
./tools/render/build.sh   # writes tools/render/out/
```
</details>

## License

Released under the [MIT License](LICENSE).
