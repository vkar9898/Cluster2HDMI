# Cluster2HDMI
A project dedicated to utilising a 7 inch LCD panel as a standalone monitor via a HDMI-parallel RGB converter and a Pico 2 fitted on a custom PCB
# Controlling a reverse-engineered 7" LCD panel from a vehicle dashboard

I have been reverse engineering a 7" LCD panel that I pulled out of a vehicle dashboard, in hopes of using it as a standalone monitor. So far I have mapped every pin on the 45-pin video connector, and the next step is designing and ordering a PCB to drive it.

<p align="center">
  <img src="images/Red.jpg" width="250">
  <img src="images/Green.jpg" width="250">
  <img src="images/Blue.jpg" width="250">
</p>

<p align="center">
  <img src="images/Main wiring.jpg" width="500">
</p>

## Why I made this

This panel comes from an Audi Q7 instrument cluster (dashboard). Prior to this, I was able to control the entire dashboard via the CAN protocol. After that, I had the dream of being able to control the LCD entirely independently. I have always found it interesting reverse engineering things and making them work how I want, so I believed this project would be a great start, and so far it has.

## What it does

In the end, I aim to have this work as a standalone monitor, working via converting HDMI to parallel RGB, with a 12V PSU powering both the panel and its backlight, and rerouting specific pins to the panel, in order to make it work.

## How it works

From my computer, a HDMI cable will be plugged into a custom PCB, where it is converted to parallel RGB, before the video-specific pins (RGB, HSYNC, VSYNC, PCLK, etc.) will be routed to the correct pins connected to the panel. A Pico 2 will replicate the SPI setup commands the dashboard originally sends to the panel, and control the backlight brightness. The 12V supply will also power the panel's logic through a 3.3V regulator, and the backlight through a constant-current LED driver.

## Reverse engineering the panel

Originally, I had tried to search for datasheets available for my panel, but this was to no avail. There is not a single public datasheet available on the internet, which meant I had to reverse engineer it myself entirely. I began by connecting the dashboard's ribbon to one FFC breakout board and the panel's flex to another, with jumper wires between them, so I could probe every pin for continuity and voltage with a multimeter while the panel was running.

### Pin map (45-pin, 0.5 mm FPC)

Numbers are the breakout board labels.

| Label | Function | Notes |
|---|---|---|
| 1, 2, 13, 22, 31, 33, 37, 44, 45 | Ground | |
| 3 | Unknown | 1.5 kΩ pull-down to ground on the cluster side |
| 4, 38 | Power in | Supplied by the cluster (voltage to be confirmed) |
| 5–12 | Blue B0–B7 | 5 = least significant bit |
| 14–21 | Green G0–G7 | 14 = least significant bit |
| 23–30 | Red R0–R7 | 23 = least significant bit |
| 32 | PCLK | Pixel clock |
| 34 | HSYNC | |
| 35 | VSYNC | |
| 36 | DE | Data enable |
| 39, 43 | Not connected | Function unknown |
| 40 | SPI data (MOSI) | Setup commands |
| 41 | SPI chip select | Active low |
| 42 | SPI clock | |

## Wiring (current test setup)

Breakout A = panel side, Breakout B = cluster side. Numbers are the breakout labels.

### Timing and SPI

| Pico 2 | Breakout A | Signal |
|---|---|---|
| GP0 | 32 | PCLK |
| GP1 | 36 | DE |
| GP2 | 34 | HSYNC |
| GP27 | 35 | VSYNC |
| GP28 | — | Not connected (used internally by the Pico) |
| GP21 | 42 | SPI clock |
| GP22 | 40 | SPI data (MOSI) |
| GP26 | 41 | SPI chip select |
| GND | Ground rail | Ground |

### Colour data (top 6 bits of each colour)

| Colour | Bit | Breakout A | Pico 2 |
|---|---|---|---|
| Blue | B2 | 7 | GP5 |
| Blue | B3 | 8 | GP6 |
| Blue | B4 | 9 | GP7 |
| Blue | B5 | 10 | GP8 |
| Blue | B6 | 11 | GP3 |
| Blue | B7 | 12 | GP9 |
| Green | G2 | 16 | GP12 |
| Green | G3 | 17 | GP13 |
| Green | G4 | 18 | GP14 |
| Green | G5 | 19 | GP4 |
| Green | G6 | 20 | GP15 |
| Green | G7 | 21 | GP10 |
| Red | R2 | 25 | GP18 |
| Red | R3 | 26 | GP19 |
| Red | R4 | 27 | GP20 |
| Red | R5 | 28 | GP11 |
| Red | R6 | 29 | GP16 |
| Red | R7 | 30 | GP17 |

### Resistors to ground

| Breakout A | Resistor | Why |
|---|---|---|
| 3 | [value] | Copies the cluster's 1.5 kΩ pull-down |
| 5, 6 | 2.2 kΩ each | Blue B0–B1 held low (unused) |
| 14, 15 | 2.2 kΩ each | Green G0–G1 held low (unused) |
| 23, 24 | 2.2 kΩ each | Red R0–R1 held low (unused) |

### Cluster to panel (breakout B → breakout A)

| Connection | Purpose |
|---|---|
| B4 → A4 | Panel power from the cluster |
| B38 → A38 | Panel power from the cluster |
| A1, 2, 13, 22, 31, 33, 37, 44, 45 → ground rail | Panel grounds |
| B1, 22, 44 → ground rail | Cluster ground |
| A39, A43 | Left unconnected |
| 10-pin backlight ribbon | Stays plugged into the cluster |

Power order: cluster on first, then plug in the Pico.

### Video timing (measured from the cluster)

| | Value |
|---|---|
| Resolution | 800 × 480 |
| Pixel clock | ~26.8 MHz (cluster), 25 MHz (my Pico driver) |
| Horizontal | HSYNC 10 px, back porch 6 px, active 800 px, front porch 106 px, total 922 px |
| Vertical | active 480 lines, front porch 8, VSYNC 4, back porch 8, total 500 lines |
| Refresh rate | ~58 Hz (cluster), ~54 Hz (Pico) |
| Sync polarity | HSYNC and VSYNC active low, DE active high |

### SPI setup sequence

3-wire SPI, mode 0, MSB first, ~500 kHz, chip select active low.
Starts ~25 ms after video starts. Without it the panel stays black.

| Step | Bytes (hex) | Delay after |
|---|---|---|
| 1 | 1B 50 00 | 2.15 ms |
| 2 | 1D 5C 00 | 2.15 ms |
| 3 | 10 00 | 2.15 ms |
| 4 | 08 80 | ~125.6 ms |
| 5 | 14 80 | |

The cluster repeats the whole set every ~545.6 ms. What each register does is unknown.

## Current status

Currently, I am able to display full-screen solid colours on the panel from the Pico: red, green and blue, as well as other colours such as cyan, magenta, white, etc. (6 bits per colour). The panel's power and backlight still come from the cluster. Next is to properly power the panel via my own power supply from a custom PCB, and be able to use it as a standalone monitor connected to my computer via HDMI.

## Hardware

<!-- Write in your own words. Facts to cover:
     - designed in KiCad, made by JLCPCB, fine-pitch connectors machine-soldered
     - 45-pin FPC socket for the panel, 40-pin FPC socket for the TFP401 ribbon
     - 10-pin connector for the backlight, socket for the Pico 2, 12V barrel jack
     - 12V → 5V buck (TFP401 board + Pico), 3.3V regulator (panel logic)
     - constant-current boost LED driver for the backlight, brightness by Pico PWM
     - 1.5 kΩ pull-down on pin 3 (copying the cluster), test pads on key signals -->

## Firmware

Currently, the Pico code is MicroPython, written and run through Thonny. It generates the timing signals (PCLK, HSYNC, VSYNC, DE) using the Pico's PIO hardware, sends the SPI setup sequence, and controls the red, green and blue bits. The test firmware was written with help from Claude (AI). In the future, it will only be doing the SPI sequence and backlight control on the PCB, as the HDMI-parallel RGB converter will be responsible for the timing and colour bits. [firmware](Firmware)

## How to flash

1. Holding BOOTSEL, plug in your Pico, and drag the [MicroPython .uf2 file](https://micropython.org/download/RPI_PICO2/) onto the drive that appears.
2. Open Thonny and choose the Pico as the interpreter, before saving the [firmware](Firmware) file onto the Pico.
3. Turn on the cluster first, then turn on the Pico. You are done!

## Known issues

* Pins 3, 39 and 43's functions are unknown
* Exactly what each SPI register does is unknown, but easily replicable
* Unknown whether the panel needs SPI commands repeated
* Panel's power and backlight still come from the cluster
* 10-pin backlight connector hasn't been reverse-engineered yet
* Pico test driver uses 6 bits per colour, not 8, and can only show solid colours
* Loose wiring can cause unexpected disconnections

## Building one yourself

Coming once the PCB is finished.

## Bill of materials

See [bom.csv](bom.csv).

## Credits & references

- [LogicAnalyzer by gusmanb](https://github.com/gusmanb/logicanalyzer)
- [Adafruit TFP401 HDMI/DVI decoder](https://www.adafruit.com/product/2219)
- Claude (AI): helped write the test firmware and decode the logic analyser captures

## Licence

MIT, see [LICENSE](LICENSE).
