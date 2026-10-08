---
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

First, I began the day with continuity checking the cluster's FFC, and I couldn't believe my eyes. The pins perfectly matched the panel's FFC, which was very happy news. It was my initial logic analysing that had been off! With this newfound knowledge, I got the Pico 2 wired to the LCD, with the cluster supplying its 10-pin connector, and some 3.3V pins on the 45-pin connector.

Here I ran into a problem. Screen turns on, backlight is on, but no colour. Nothing at all, the screen was entirely black. I was shocked, I believed I did everything right!

After contemplating, I decided to logic analyse again, on a fresh afternoon, with the FFC seated correctly. This time, I logic analysed all the pins that were showing low on October 7th captures. Bingo! I had found that pins 40, 41, and 42 were showing some sort of SPI sequence, so I decided to dig deeper. I thought using burst mode in the LogicAnalyzer app would help, but it didn't, and re-triggered instantly, giving tiny 200ns gaps, so I decided to switch to long captures. Here I was able to see the signal properly, see all of its timings correctly, and replicate it in MicroPython with the help of Claude. After getting the Pico 2 tediously wired to the LCD, the moment of truth was about to be shown...

And it did! The LCD glowed a blue-grey, signalling that there it was missing some green and most of its red. I decided to run a walk test with the slider tool, lighting one data pin at a time and noting its colour and brightness, which showed the strongest bits of each colour were the ones held low by resistors. I replaced six Pico wires off the weakest bits and onto the strongest bits, and moved the resistors onto the weakest bits, and I got all 3, red, green and blue! I was able to show a few different colours on the LCD, primarily red, green, blue, black, white, grey, cyan, magenta, and yellow. This was a huge win, so I decided to again call it a day, and proceed with the 10-pin connector another day.

<img src="https://raw.githubusercontent.com/vkar9898/Cluster2HDMI/main/images/Blue.jpg" width="400">

**Total time spent: 5 hours**
