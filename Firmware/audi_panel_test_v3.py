# audi_panel_test_v3.py
# Pico 2 (RP2350) + MicroPython
# Audi Q7 4M cluster LCD (800x480 parallel RGB) - timing + SPI setup + colour.
#
# New in v3: the Pico now drives the TOP 6 bits of each colour (it had the
# bottom bits before, and the top bits were held low - that's why white
# looked blue-grey). Colour bit layout, confirmed by the slider walk:
#   Blue  = labels 5..12  (5 = weakest bit, 12 = strongest)
#   Green = labels 14..21
#   Red   = labels 23..30
#
# Save on the Pico as main_v3.py (or main.py so it starts by itself).
# Shell commands:
#   white()  black()  rgb(r, g, b)   (0-255 each, e.g. rgb(255, 128, 0) = orange)
#   red() green() blue() yellow() cyan() magenta() grey()
#   demo()                cycle through the colours, 2 s each
#   only(label)  label(label, 0/1)  walk()
#   send_setup()  auto_refresh(False/True)  stop()
#
# ---------------------------------------------------------------
# WIRING (Pico 2 GPIO -> breakout A label)
#   GP0  -> 32  PCLK
#   GP1  -> 36  DE
#   GP2  -> 34  HSYNC
#   GP27 -> 35  VSYNC
#   GP28 -> NOTHING (internal flag)
#   GP21 -> 42  SPI clock
#   GP22 -> 40  SPI data
#   GP26 -> 41  SPI chip select
#   GP3..GP20 -> data labels, see DATA below
#   2.2k to ground on: A3 (as before), A5, A6, A14, A15, A23, A24
#   GND  -> ground rail
# Power order: cluster ON first, then plug in the Pico and press Run.
# ---------------------------------------------------------------

import rp2
import machine
from machine import Pin, Timer
import micropython
import time

PCLK_GP  = 0
DE_GP    = 1
HSYNC_GP = 2
VSYNC_GP = 27
VACT_GP  = 28

SPI_SCK_GP  = 21   # -> label 42
SPI_MOSI_GP = 22   # -> label 40
SPI_CS_GP   = 26   # -> label 41

# (Pico GPIO, breakout label) - top 6 bits of each colour, weakest first
BLUE_BITS  = [(5, 7), (6, 8), (7, 9), (8, 10), (3, 11), (9, 12)]
GREEN_BITS = [(12, 16), (13, 17), (14, 18), (4, 19), (15, 20), (10, 21)]
RED_BITS   = [(18, 25), (19, 26), (20, 27), (11, 28), (16, 29), (17, 30)]
DATA = BLUE_BITS + GREEN_BITS + RED_BITS

# ---- setup commands captured from the cluster ----------------
SETUP_GROUP = [
    bytes([0x1B, 0x50, 0x00]),
    bytes([0x1D, 0x5C, 0x00]),
    bytes([0x10, 0x00]),
    bytes([0x08, 0x80]),
]
GROUP_GAP_US  = 2150          # gap between the four commands
LATE_CMD      = bytes([0x14, 0x80])
LATE_DELAY_MS = 126           # sent ~125.6 ms after the group
REPEAT_MS     = 546           # whole set repeats every ~545.6 ms

# ---- timing ---------------------------------------------------
PIO_FREQ = 50_000_000     # 25 MHz pixel clock
H_ACTIVE = 800
H_FP     = 106
V_ACTIVE = 480


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW,
             set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH))
def htiming():
    pull()                .side(0)
    mov(y, osr)           .side(0)
    pull()                .side(0)
    wrap_target()
    set(pins, 0)          .side(0)
    set(x, 8)             .side(1)
    label("hs")
    nop()                 .side(0)
    jmp(x_dec, "hs")      .side(1)
    set(pins, 2)          .side(0)
    set(x, 3)             .side(1)
    label("bp")
    nop()                 .side(0)
    jmp(x_dec, "bp")      .side(1)
    mov(x, osr)           .side(0)
    jmp(pin, "act")       .side(1)
    set(pins, 2)          .side(0)
    jmp("px")             .side(1)
    label("act")
    set(pins, 3)          .side(0)
    nop()                 .side(1)
    label("px")
    nop()                 .side(0)
    jmp(x_dec, "px")      .side(1)
    set(pins, 2)          .side(0)
    mov(x, y)             .side(1)
    label("fp")
    nop()                 .side(0)
    jmp(x_dec, "fp")      .side(1)
    wrap()


@rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW))
def vtiming():
    pull()                .side(1)
    wrap_target()
    wait(1, gpio, 2)      .side(1)
    wait(0, gpio, 2)      .side(1)
    mov(x, osr)           .side(3)
    label("a")
    wait(1, gpio, 2)      .side(3)
    wait(0, gpio, 2)      .side(3)
    jmp(x_dec, "a")       .side(3)
    wait(1, gpio, 2)      .side(3)
    wait(0, gpio, 2)      .side(3)
    set(x, 6)             .side(1)
    label("f")
    wait(1, gpio, 2)      .side(1)
    wait(0, gpio, 2)      .side(1)
    jmp(x_dec, "f")       .side(1)
    wait(1, gpio, 2)      .side(1)
    wait(0, gpio, 2)      .side(1)
    set(x, 2)             .side(0)
    label("s")
    wait(1, gpio, 2)      .side(0)
    wait(0, gpio, 2)      .side(0)
    jmp(x_dec, "s")       .side(0)
    wait(1, gpio, 2)      .side(0)
    wait(0, gpio, 2)      .side(0)
    set(x, 6)             .side(1)
    label("b")
    wait(1, gpio, 2)      .side(1)
    wait(0, gpio, 2)      .side(1)
    jmp(x_dec, "b")       .side(1)
    wrap()


# ---- SPI (bit-banged, mode 0: data set while clock low, read on rising edge)
spi_cs   = Pin(SPI_CS_GP, Pin.OUT, value=1)
spi_sck  = Pin(SPI_SCK_GP, Pin.OUT, value=0)
spi_mosi = Pin(SPI_MOSI_GP, Pin.OUT, value=0)

def spi_write(frame):
    spi_cs(0)
    for byte in frame:
        for bit in range(7, -1, -1):
            spi_mosi((byte >> bit) & 1)
            spi_sck(1)
            spi_sck(0)
    spi_mosi(0)
    spi_cs(1)

def send_group():
    for f in SETUP_GROUP:
        spi_write(f)
        time.sleep_us(GROUP_GAP_US)

def send_setup():
    send_group()
    time.sleep_ms(LATE_DELAY_MS)
    spi_write(LATE_CMD)
    print("setup commands sent")

_t_cycle = Timer()
_t_late = Timer()

def _late(_):
    spi_write(LATE_CMD)

def _cycle_sched(_):
    send_group()
    _t_late.init(mode=Timer.ONE_SHOT, period=LATE_DELAY_MS,
                 callback=lambda t: micropython.schedule(_late, 0))

def auto_refresh(on=True):
    if on:
        _t_cycle.init(mode=Timer.PERIODIC, period=REPEAT_MS,
                      callback=lambda t: micropython.schedule(_cycle_sched, 0))
        print("auto refresh on (every %d ms)" % REPEAT_MS)
    else:
        _t_cycle.deinit()
        _t_late.deinit()
        print("auto refresh off")


# ---- start video ----------------------------------------------
data_pins = [Pin(gp, Pin.OUT, value=0) for gp, _ in DATA]
by_label = {lab: data_pins[i] for i, (_, lab) in enumerate(DATA)}

sm_v = rp2.StateMachine(4, vtiming, freq=machine.freq(),
                        sideset_base=Pin(VSYNC_GP))
sm_h = rp2.StateMachine(0, htiming, freq=PIO_FREQ,
                        sideset_base=Pin(PCLK_GP),
                        set_base=Pin(DE_GP),
                        jmp_pin=Pin(VACT_GP))
sm_v.put(V_ACTIVE - 2)
sm_h.put(H_FP - 2)
sm_h.put(H_ACTIVE - 2)
sm_v.active(1)
sm_h.active(1)


# ---- helpers --------------------------------------------------
def white():
    for p in data_pins:
        p.value(1)

def black():
    for p in data_pins:
        p.value(0)

def label(lab, v):
    by_label[lab].value(1 if v else 0)

def only(lab):
    black()
    label(lab, 1)

def rgb(r, g, b):
    """Fill the screen with one colour, 0-255 per channel (bottom 2 bits ignored)."""
    for val, bits in ((r, RED_BITS), (g, GREEN_BITS), (b, BLUE_BITS)):
        for i, (gp, lab) in enumerate(bits):
            by_label[lab].value((val >> (i + 2)) & 1)

def red():     rgb(255, 0, 0)
def green():   rgb(0, 255, 0)
def blue():    rgb(0, 0, 255)
def yellow():  rgb(255, 255, 0)
def cyan():    rgb(0, 255, 255)
def magenta(): rgb(255, 0, 255)
def grey():    rgb(128, 128, 128)

COLOURS = [("white", white), ("red", red), ("green", green), ("blue", blue),
           ("yellow", yellow), ("cyan", cyan), ("magenta", magenta),
           ("grey", grey), ("black", black)]

def demo(delay=2):
    for name, fn in COLOURS:
        fn()
        print(name)
        time.sleep(delay)
    white()

def walk(delay=3):
    for gp, lab in DATA:
        only(lab)
        print("label", lab, "(GP%d) on - note the colour and brightness" % gp)
        time.sleep(delay)
    black()
    print("done")

def stop():
    auto_refresh(False)
    sm_h.active(0)
    sm_v.active(0)
    black()
    print("stopped")


# ---- go -------------------------------------------------------
white()
time.sleep_ms(50)          # cluster starts SPI ~25 ms after video; give it a bit more
send_setup()
auto_refresh(True)
print("Video running (800x480, 25 MHz). Screen should be white.")
print("Commands: white() black() rgb(r,g,b) red() green() blue() demo() only(label) walk() stop()")
