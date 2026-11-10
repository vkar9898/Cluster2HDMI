# Cluster2HDMI
A project that converts a 7" screen from a car dashboard to a standalone monitor.

<p align="center">
  <img src="images/Red.jpg" width="250">
  <img src="images/Green.jpg" width="250">
  <img src="images/Blue.jpg" width="250">
</p>

<p align="center">
  <img src="images/Main wiring.jpg" width="500">
  <img src="images/pcbfront.png" width="300">
  <img src="images/pcbback.png" width="300">
  <img src="images/case1.png" width="300">
  <img src="images/case2.png" width="300">
</p>

## Why I made this

This screen comes from an Audi Q7 dashboard. Prior to this project, I was able to control the entire dashboard via CAN. After that, I wanted to control the LCD entirely independently, and use it as a standalone monitor. I have always found it interesting to reverse engineering things, so I believed this project would be a great start, and so far it has.

## What it does

This is a standalone monitor, so it can display graphics or what not connected directly to your PC.

## How it works

A HDMI cable will be plugged into the case, it will function as a secondary monitor, converting HDMI to Parallel RGB on the PCB, via a TFP401 microchip, and sending a  SPI sequence from a Pico 2 to the panel.

## Reverse engineering the panel

Originally, I had tried to search for datasheets available for my panel, but couldn't find any. This meant I had to reverse engineer it myself entirely. I began by connecting the dashboard's ribbon to one FFC breakout board and the panel's flex to another, with jumper wires between them, so I could probe every pin for continuity and voltage with a multimeter while the panel was running. Many problems were met here, more in the [journal](JOURNAL.md).

### Pin map (45-pin, 0.5 mm FPC)

Numbers are the breakout board labels.

| Label | Function | Notes |
|---|---|---|
| 1, 2, 13, 22, 31, 33, 37, 44, 45 | Ground | |
| 3 | Unknown | 1.5 kΩ pull-down to ground |
| 4, 38 | Power in | 3.3V |
| 5–12 | Blue B0–B7 | 5 = smallest bit |
| 14–21 | Green G0–G7 | 14 = smallest bit |
| 23–30 | Red R0–R7 | 23 = smallest bit |
| 32 | PCLK | Pixel clock |
| 34 | HSYNC | |
| 35 | VSYNC | |
| 36 | DE | Data enable |
| 39, 43 | Not connected | Unknown |
| 40 | SPI data (MOSI) | Setup commands |
| 41 | SPI chip select | Active low |
| 42 | SPI clock | |

### Video timing (measured from the cluster)

| | Value |
|---|---|
| Resolution | 800 × 480 |
| Pixel clock | ~26.8 MHz (cluster), 25 MHz (Pico) |
| Horizontal | HSYNC 10 px, back porch 6 px, active 800 px, front porch 106 px, total 922 px |
| Vertical | active 480 lines, front porch 8, VSYNC 4, back porch 8, total 500 lines |
| Refresh rate | ~58 Hz (cluster), ~54 Hz (Pico) |
| Sync polarity | HSYNC and VSYNC active low, DE active high |

### SPI setup sequence

The sequence that the cluster sends to the panel to 'stay alive', or a gamma/brightness setting. It consists of 3 wires at ~500 kHz. It starts ~25 ms after video starts, and without it the panel stays black.

| Step | Bytes (hex) | Delay after |
|---|---|---|
| 1 | 1B 50 00 | 2.15 ms |
| 2 | 1D 5C 00 | 2.15 ms |
| 3 | 10 00 | 2.15 ms |
| 4 | 08 80 | ~125.6 ms |
| 5 | 14 80 | |

The cluster repeats the whole set every ~545.6 ms. What each register does is unknown.

## Current status

The design is finished, including the PCB, case, and firmware, and is waiting on funding to order and build.

## Wiring (current test setup)

Breakout A = panel side, Breakout B = cluster side.

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
| 3 | 1 kΩ | 1.5 kΩ pull-down |
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

## Hardware

The TFP401 converts HDMI to parallel RGB, and the SPI sequence comes from the Pico
### Video path
HDMI input, into the TFP401 chip, outputting TTL/Parallel RGB, and connects to the 45-pin connector
### Power
12V input, converted to 5V, 3.3V, and 22.5V, via buck converters and boost converters, with a resettable fuse (F2)
### Backlight
Driven by the 22.5V, with 3 LED strings that return through a 20mA constant-current chip. A MOSFET then switches them with PWM from the Pico for brightness.
### Pico 2
SPI sequence on pins 4-6 of the 45-pin connector, the backlight, and the EDID.
### EDID
A memory chip (AT24C02 EEPROM) on the HDMI's DDC lines. The Pico writes it through a level shifter, and it tells the PC the screens resolution, and monitor name.

## Firmware

Currently, the Pico code is MicroPython, written and run through Thonny. It generates the timing signals (PCLK, HSYNC, VSYNC, DE) using the Pico's PIO hardware, sends the SPI  sequence, and controls the red, green and blue bits. The test firmware was written with help from Claude (AI), and is able to send the SPI sequence, turn backlight on, and write the EDID with the correct resolution and monitor name. Code can be found [here](Firmware), the file is cluster2hdmi_main.py. It is still, however, untested, as the PCB hasn't been ordered yet.

## How to flash

1. Holding BOOTSEL, plug in your Pico, and drag the [MicroPython .uf2 file](https://micropython.org/download/RPI_PICO2/) onto the drive that appears.
2. Open Thonny and choose the Pico as the interpreter, before saving the [firmware](Firmware) file onto the Pico as "main.py". After this, it'll run automatically on power-up. 
3. Turn on the Pico 2, and the software should run!

## Known issues

* Pins 3, 39 and 43's functions are unknown
* Exactly what each SPI register does is unknown, but easily replicable
* Unknown whether the panel needs SPI commands repeated
* Pico test driver uses 6 bits per colour, not 8, and can only show solid colours
* Loose wiring can cause unexpected disconnections

## Building one yourself

1. Ordering all required parts: BOM, + specific JLC parts. Gerbers available in KiCad/Cluster2HDMI/gerbers.zip, and JLC BOM and CPL are in KiCad/Fabrication
2. Soldering the 20pin female headers for the Pico 2 is required, as JLC is out of stock of them
3. Printing the case, case_shell.stl and case_back_cover.stl
4. Putting it together: PCB screws onto 2 posts on the back cover with M2x8 screws, 45-pin and 10-pin ribbons connect to the board, Pico to its socket, and finally, the cover going into the shell, with 2 M2 x 30 screws going through the cover into the panel's top holes
5. Powering it up, the Pico writes the EDID, so the cable needs unplugging and replugging once before the PC sees the screen properly.

## Bill of Materials

All prices in USD (AliExpress prices converted from AUD). Full list with notes: [bom.csv](bom.csv). Every part on the PCB (with LCSC numbers) is in [KiCad/Fabrication/Cluster2HDMI_BOM_JLC_v2.csv](KiCad/Fabrication/Cluster2HDMI_BOM_JLC_v2.csv).

| Section | Item | Designators / use | Part # / search term | Supplier | Qty | Unit price (USD) | Line total (USD) | Price status | Link | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| PCB + assembly | Multi-Cluster-Control PCB, 5 boards, 2 assembled (Economic PCBA, 1 oz, top side) | Whole board, all JLC-placed parts | Gerbers + BOM + CPL from Fabrication Toolkit | JLCPCB | 1 | $65.70 | $65.70 | Quoted | [link](https://jlcpcb.com) | PCB $9.80 + PCBA $55.90 |
| PCB + assembly | JLCPCB coupon |  |  | JLCPCB | 1 | -$10.00 | -$10.00 | Quoted |  |  |
| PCB + assembly | Keystone 3568 mini-blade fuse holder (idle parts) | F1, F2 (2 boards) | C5249699 | JLCPCB parts cart | 4 | $1.21 | $4.84 | Quoted | [link](https://jlcpcb.com/partdetail/C5249699) | Idle parts |
| Board parts not assembled by JLC | Cluster plug, 10-pin 3.81 mm screw (KANGNEX WJ15EDGK-3.81-10P-14-00A) | CN1-CN3, 2 per header | C26865 | LCSC | 6 | $0.8112 | $4.87 | Quoted | [link](https://www.lcsc.com/product-detail/C26865.html) |  |
| Board parts not assembled by JLC | Cluster plug, 4-pin 3.81 mm screw (KANGNEX WJ15EDGK-3.81-04P-14-00A) | CN4, 2 per header | C7244 (min order 5) | LCSC | 5 | $0.3082 | $1.54 | Quoted | [link](https://www.lcsc.com/product-detail/C7244.html) | Min order 5 |
| Board parts not assembled by JLC | 5-way screw terminal, 5.08 mm (Phoenix MKDS 1,5/5-5,08, 1715750) | J15 | C6042418 | LCSC | 2 | $1.2721 | $2.54 | Quoted | [link](https://www.lcsc.com/product-detail/C6042418.html) | 1 spare |
| Board parts not assembled by JLC | 1x14 female header 2.54 mm | J11 (VID6606 adapter), 2 per board | C2905420 (min order 5) | LCSC | 5 | $0.1580 | $0.79 | Quoted | [link](https://www.lcsc.com/product-detail/C2905420.html) | Min order 5 |
| Modules and chips | VID6606 stepper driver, SOP-28 (5 pcs) | X-90 speedo stepper driver | VID6606 | AliExpress | 1 | $4.61 | $4.61 | Quoted | [link](https://www.aliexpress.com/item/1005007323081013.html) |  |
| Modules and chips | SOP-28 to DIP-28 adapter boards (10 pcs) | Carrier for the VID6606 in J11 | SOP28 to DIP28 | AliExpress | 1 | $1.73 | $1.73 | Quoted | [link](https://www.aliexpress.com/item/32909339596.html) | 15.24 mm DIP width |
| Modules and chips | X27.168 gauge stepper motor | X-90 speedo + 1 spare | X27.168 | AliExpress | 2 | $2.35 | $4.70 | Quoted | [link](https://www.aliexpress.com/item/1005006620561935.html) |  |
| Modules and chips | PCA9685 16-ch PWM module | J5/J6 (gauge PWM) | PCA9685 | AliExpress | 1 | $3.79 | $3.79 | Quoted | [link](https://www.aliexpress.com/item/1005005670283526.html) |  |
| Modules and chips | MCP2515 CAN module, TJA1050, 8 MHz | Second CAN module | MCP2515 TJA1050 | AliExpress | 1 | $0.92 | $0.92 | Quoted | [link](https://www.aliexpress.com/item/1005010199935143.html) | 8 MHz crystal |
| Modules and chips | MP1584EN adjustable buck module (5 pcs) | M5 (5.0 V), M6 (3.6 V) | MP1584EN | AliExpress | 1 | $3.15 | $3.15 | Quoted | [link](https://www.aliexpress.com/item/1005007653423578.html) | Set voltage before soldering |
| Modules and chips | MT3608 boost module | M7 (24 V) | MT3608 / 1PCS | AliExpress | 1 | $2.38 | $2.38 | Quoted | [link](https://www.aliexpress.com/item/1005011548818999.html) | Set to 24 V |
| Wiring | 20-core 20 AWG RVV sheathed cable, 2 m | 4 cluster cables x 0.5 m | RVV 20 core 20 AWG, 2 m option | AliExpress | 1 | $18.73 | $18.73 | Quoted | [link](https://www.aliexpress.com/item/1005004200589656.html) |  |
| Wiring | Dupont jumpers, female-female, 10 cm, 40 pcs | PCA9685, MCP2515 x2, light sensor | Dupont F-F 10 cm | AliExpress | 1 | $0.99 | $0.99 | Quoted | [link](https://www.aliexpress.com/item/1005009372155336.html) |  |
| Power | 12 V 4 A plug pack, 5.5 x 2.1 mm, AU plug | J1, J2 | 4A/12 V/AU Plug | AliExpress | 2 | $4.19 | $8.38 | Quoted | [link](https://www.aliexpress.com/item/1005013455261196.html) | Centre-positive |
| Power | SCA mini blade fuse 5 A, 6 pack | F1, F2 + spares | 726696 | Supercheap Auto | 1 | $2.81 | $2.81 | Quoted | [link](https://www.supercheapauto.com.au/p/sca-sca-automotive-fuses-mini-blade-5-amp-6-pack/726696.html) | Click & collect |
| Lighting | T10 (W5W) LED wedge bulbs, 6500K white, 10 pack | Cluster illumination | ASIN B0HGLD6KBJ | Amazon AU | 1 | $6.33 | $6.33 | Quoted | [link](https://www.amazon.com.au/dp/B0HGLD6KBJ) | Polarised |
| Mounting | M3 x 16 mm pan head screws + M3 nuts | Board to support, 4 holes | M3 x 16 machine screws + nuts | Bunnings | 1 | $3.52 | $3.52 | Estimate |  |  |
| Discounts | AliExpress checkout discounts |  |  | AliExpress | 1 | -$4.34 | -$4.34 | Quoted |  |  |
| Already owned | ESP32 dev board (38-pin) | J3/J4 |  | Owned | 1 | $0.00 | $0.00 | Owned |  |  |
| Already owned | Light sensor module | J14 |  | Owned | 1 | $0.00 | $0.00 | Owned |  |  |
| Already owned | MCP2515 CAN module (first one) | J7 or J9 |  | Owned | 1 | $0.00 | $0.00 | Owned |  |  |
| Shipping | Shipping: DHL Express (PCB + assembly + idle parts) |  |  | JLCPCB | 1 | $18.11 | $18.11 | Quoted |  |  |
| Shipping | Shipping: Global Direct Standard Line |  |  | LCSC | 1 | $9.93 | $9.93 | Quoted |  |  |
| Shipping | Shipping: Handling fee |  |  | LCSC | 1 | $3.00 | $3.00 | Quoted |  | Waived over $15.55 merchandise |
| Shipping | Shipping: Dupont jumper store |  |  | AliExpress | 1 | $3.08 | $3.08 | Quoted |  |  |
| Shipping | Shipping: MCP2515 store |  |  | AliExpress | 1 | $2.27 | $2.27 | Quoted |  |  |
| Shipping | Shipping: All other items |  |  | AliExpress | 1 | $0.00 | $0.00 | Quoted |  | Free shipping |
| Shipping | Shipping: Click & collect |  |  | Supercheap Auto | 1 | $0.00 | $0.00 | Quoted |  |  |
| Shipping | Shipping: Standard delivery (T10 bulbs) |  |  | Amazon AU | 1 | $0.00 | $0.00 | Estimate |  | Free over AU$49 |
 
**Total: $164.37** (parts $127.98 + shipping $36.39)

## Credits & references

- [LogicAnalyzer by gusmanb](https://github.com/gusmanb/logicanalyzer)
- [Adafruit TFP401 HDMI/DVI decoder](https://www.adafruit.com/product/2219)
- Claude (AI): helped write the test firmware, decode the logic analyser captures, routing the PCB, and aided with designing the case

## Licence

MIT, see [LICENSE](LICENSE).
