<img width="1906" height="1005" alt="image" src="https://github.com/user-attachments/assets/02d9b382-ab21-4f5c-a1c9-bf347705bac9" />---
title: "Cluster2HDMI"
author: "vkar9898"
description: "A project dedicated to utilising a 7 inch LCD panel from a car dashboard as a standalone monitor via a HDMI-parallel RGB converter and a Pico 2 fitted on a custom PCB."
created_at: "2026-10-07"
---

# October 7: Began reverse engineering

Started reverse engineering with the FFC cable misaligned by one pin, and didn't realise the mistake; spent a long time continuity checking and voltage metering to figure out the issue.

I began with basic voltage measuring, to ensure that my Pico wouldn't get fried when logic analysing (inputs must be under 3.3V). After concluding that all pins on the 45 pin connector were under or about 3.3V, I was ready to begin reverse engineering.

I did it 4 pins at a time, as this wasn't too messy and didn't get out of hand too easily. It also allowed more samples than doing most pins at once, which was a nice side benefit. Once I was able to set up the Pico 2 as an analyser with gusmanb's LogicAnalyzer, I was able to begin analysing by placing a jumper between GP0 and GP1 for triggering to work. Initially, when measuring, I deduced that PCLK was 31, HSYNC was 33, and DE was 35, with no VSYNC. I had assumed that VSYNC didn't exist on the panel and it used DE as a way of refreshing, and also failed to realise there was a setup sequence.

After the first logic analysing section, I moved onto continuity checking the panel itself, where I ran into many problems. The first problem was that the panel's FFC ribbon has two notches on its sides, while my breakout board doesn't have space for those notches. This resulted in a slightly angled FFC connection, which messed up many readings beyond pin 30. Pins such as 33 and 35 had continuity with ground, which is not possible. After realising this, I attempted to reseat the adapter many times, and ended up needing to cut notches in the breakout board specifically to fit the FFC.

After cutting notches, the FFC sat nicely in the breakout board, but then I ran into another problem. No matter how many times I reseated it, it was always 1 pin off my logic analysing. As it was already getting quite late, I decided to call it a day, and went to sleep.

<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/wiring_oct7.jpg" width="400">

**Total time spent: 6 hours**

# October 8: LCD works! But after a lot of tries

First, I began the day with continuity checking the cluster's FFC, and I couldn't believe my eyes. The pins perfectly matched the panel's FFC, which was very happy news. It was my initial logic analysing that had been off! With this newfound knowledge, I got the Pico 2 wired to the LCD, with the cluster supplying its 10-pin connector, and supplying power pins 4 and 38 through the cluster pins 4 and 38.

Here I ran into a problem. Screen turns on, backlight is on, but no colour. Nothing at all, the screen was entirely black. I was shocked, I believed I did everything right!

After contemplating, I decided to logic analyse again, on a fresh afternoon, with the FFC seated correctly. This time, I logic analysed all the pins that were showing low on October 7th captures. Bingo! I had found that pins 40, 41, and 42 were showing some sort of SPI sequence, so I decided to dig deeper. I thought using burst mode in the LogicAnalyzer app would help, but it didn't, and re-triggered instantly, giving tiny 200ns gaps, so I decided to switch to long captures. Here I was able to see the signal properly, see all of its timings correctly, and replicate it in MicroPython with the help of Claude. After getting the Pico 2 tediously wired to the LCD, the moment of truth was about to be shown...

And it did! The LCD glowed a blue-grey, signalling that there it was missing some green and most of its red. I decided to run a walk test with the slider tool, lighting one data pin at a time and noting its colour and brightness, which showed the strongest bits of each colour were the ones held low by resistors. I replaced six Pico wires off the weakest bits and onto the strongest bits, and moved the resistors onto the weakest bits, and I got all 3, red, green and blue! I was able to show a few different colours on the LCD, primarily red, green, blue, black, white, grey, cyan, magenta, and yellow. This was a huge win, so I decided to again call it a day, and proceed with the 10-pin connector another day.

<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/Blue.jpg" width="400">

**Total time spent: 5 hours**

# October 9: 10-pin connector testing, beginning to start designing custom PCB

Began testing the 10-pin connector for continuity and overall voltage. Found that pin 1, 4, 7, 10 are most likely unused (no continuity, no voltages, maybe sends signals back to the cluster?), 8, 9 function as LED + (~22.5V), 3, 5 and 6 are LED- (3V), and 2 is ground. The cluster reboots if the 10-pin isn't connected, so it probably has upstream and downstream pins. Currently thinking about how I design my own HDMI to parallel RGB adapter, using the TFP401APZPR microchip.

Picked out parts for my PCBA, and checked each LCSC number to ensure it's compatible with JLCPCB. Installed KiCad10 and easyeda2kicad, and imported some symbols and footprints from LCSC with it. Places teh wrong chip first, then swapped it for the right one, as the library path was wrong, so I had to import the footprint library manually.

Setup the TFP401, it's power, the 45-pin panel connector, HDMI input, EDID, and Pico 2 in a schematic. PCB design coming soon. Encountered some minor errors in KiCad, but fixed them easily.
Recording: https://lapse.hackclub.com/timelapse/lRLIcTCkxbhM (can't add two lapse files to Forge)

<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/testing_oct9.png" width="400">
<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/schematic.png" width="400">

**Total time spent: 4 hours**

# October 10: Finishing off PCB designing

Figured out how many layers to use on my board, decided to do 4 layers to allow for high speed HDMIS to pass through, with layers top/gnd/pwr/bottom. Calculated track width and gap for the HDMI pairs, worked out with JLC's impedance calculater (100 ohms), and set out a rule set for normal signals, power, and HDMI to make sure everything would work. 

Measured the LCD panel, and decided to build the board same width as it but a little shorter, to allow for a case later. The PCB will use two screws that are available on the current LCD, and allows the 45-pin pannel connector to slide in nicely, and the 10-pin connector to slide in well. Printed the PCB on paper to double-check everything lines up, everything did.

Next was deciding what placement to do, I decided to put HDMI socket on the top edge with the TFP401 under it. This minimises travel between the HDMI and the TFP401, and is also easy to me as I have a HDMI cable with a twisting mechanism. The Pico 2 will be placed in a socket top-right, USB pointing at the right edge (for coding). Figured the PSU would be nicest to be on the bottom right, and so its from the panels face, rather than an edge.

I ran into a few problems here too, mostly regarding pin orders and mirroring, specifically the HDMI socket's pins being mirrored relative to the TFP401's, to which the fix was copying Adafruit's TFP board: two pairs loop around under the socket, and two pairs swap over using vias. The 28 colour/sync/clock wires were also mirrored, which meant they'd have to cross over using vias through the bottom layer. 

<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/oct10pcb.png" width="400">

**Total time spent: 4 hours**
