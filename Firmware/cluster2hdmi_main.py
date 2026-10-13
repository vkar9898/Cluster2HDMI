# cluster2hdmi_main.py
#
# Pin map 
#   GP4  (pin 6)   EDID_SDA  I2C0 SDA -> PCA9306 -> HDMI DDC / EEPROM
#   GP5  (pin 7)   EDID_SCL  I2C0 SCL
#   GP6  (pin 9)   EDID_WE   high = EEPROM write enabled (Q1 pulls WP low)
#   GP7  (pin 10)  TFP_PD    low = TFP401 powered down (R1 pull-up keeps it on)
#   GP8  (pin 11)  SCDT      input, high = TFP401 sees a valid HDMI/DVI signal
#   GP9  (pin 12)  OCK_INV   TFP401 pixel clock polarity (R3 pull-up = high). Left as input by default
#   GP10 (pin 14)  BL_PWM    Q2 gate, PWM = LED brightness (R23 pull-down = off)
#   GP11 (pin 15)  BL_EN     TPS61169 backlight boost enable
#   GP17 (pin 22)  LCD_CS    panel SPI chip select (active low)
#   GP18 (pin 24)  LCD_SCK   SPI0 SCK
#   GP19 (pin 25)  LCD_MOSI  SPI0 TX
#
# Shell commands:
#   brightness(0-100)   backlight(True/False)   status()
#   edid_check()        edid_write(force=True)  edid_dump()
#   ock_inv(0/1/None)   send_setup()

import time
import micropython
from machine import Pin, PWM, SPI, I2C

# settings
BRIGHTNESS_DEFAULT = 80        # %
PWM_FREQ = 20_000              # Hz for BL_PWM 
SIGNAL_LOST_MS = 3000          # backlight goes off this long after the PC stops sending video
SETUP_DELAY_MS = 50            # wait after video appears before sending the SPI setup (cluster does ~25 ms)
FADE_MS = 400                  # backlight fade time
USE_HW_SPI = True              # False = bit-banged SPI like the breadboard test firmware

# SPI setup commands
SETUP_GROUP = [
    bytes([0x1B, 0x50, 0x00]),
    bytes([0x1D, 0x5C, 0x00]),
    bytes([0x10, 0x00]),
    bytes([0x08, 0x80]),
]
GROUP_GAP_US = 2150            # gap between the four commands
LATE_CMD = bytes([0x14, 0x80])
LATE_DELAY_MS = 126            # sent ~125.6 ms after the group
REPEAT_MS = 546                # whole set repeats every ~545.6 ms

# Video timing for the EDID - porches/sync measured from the cluster, clock raised for 60 Hz
H_ACTIVE, H_FP, H_SYNC, H_BP = 800, 106, 10, 6       # total 922
V_ACTIVE, V_FP, V_SYNC, V_BP = 480, 8, 4, 8          # total 500
REFRESH_HZ = 60
SCREEN_MM = (156, 94)                                # visible area
MONITOR_NAME = "Cluster2HDMI"     # name Windows shows in Settings > Display. 13 characters max
PRODUCT_CODE = 1                  # add 1 to this whenever you change MONITOR_NAME, so Windows treats it as a new monitor
EDID_ADDR = 0x50

# pins
led = Pin("LED", Pin.OUT, value=0)
tfp_pd = Pin(7, Pin.OUT, value=1)                    # keep TFP401 on
scdt = Pin(8, Pin.IN)
ock = Pin(9, Pin.IN)                                 # leave to the pull-up
edid_we = Pin(6, Pin.OUT, value=0)                   # EEPROM write-protected
bl_en = Pin(11, Pin.OUT, value=0)
bl_pwm = PWM(Pin(10))
bl_pwm.freq(PWM_FREQ)
bl_pwm.duty_u16(0)
lcd_cs = Pin(17, Pin.OUT, value=1)

if USE_HW_SPI:
    spi = SPI(0, baudrate=500_000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB,
              sck=Pin(18), mosi=Pin(19), miso=Pin(16))   # GP16 isn't connected, MISO unused
else:
    spi = None
    _sck = Pin(18, Pin.OUT, value=0)
    _mosi = Pin(19, Pin.OUT, value=0)

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)


# panel SPI
def spi_write(frame):
    lcd_cs(0)
    if spi:
        spi.write(frame)
    else:
        for byte in frame:
            for bit in range(7, -1, -1):
                _mosi((byte >> bit) & 1)
                _sck(1)
                _sck(0)
        _mosi(0)
    lcd_cs(1)


def send_group():
    for f in SETUP_GROUP:
        spi_write(f)
        time.sleep_us(GROUP_GAP_US)


def send_setup():
    """Send the full setup once (group, then the late command 126 ms later)."""
    send_group()
    time.sleep_ms(LATE_DELAY_MS)
    spi_write(LATE_CMD)


# backlight
def _load_brightness():
    try:
        with open("brightness.txt") as f:
            return max(0, min(100, int(f.read())))
    except Exception:
        return BRIGHTNESS_DEFAULT


_level = _load_brightness()     # % wanted
_duty = 0                       # current duty 0-65535
_bl_on = False


def _set_duty(d):
    global _duty
    _duty = max(0, min(65535, int(d)))
    bl_pwm.duty_u16(_duty)


def _fade_to(target):
    steps = 20
    start = _duty
    for i in range(1, steps + 1):
        _set_duty(start + (target - start) * i / steps)
        time.sleep_ms(FADE_MS // steps)


def backlight(on):
    global _bl_on
    if on:
        bl_en(1)
        time.sleep_ms(5)
        _fade_to(_level * 65535 // 100)
    else:
        _fade_to(0)
        bl_en(0)
    _bl_on = bool(on)
    led(1 if on else 0)


def brightness(pct):
    """Set brightness 0-100 % and remember it after power-off."""
    global _level
    _level = max(0, min(100, int(pct)))
    if _bl_on:
        _fade_to(_level * 65535 // 100)
    try:
        with open("brightness.txt", "w") as f:
            f.write(str(_level))
    except Exception:
        pass
    print("brightness", _level, "%")


def ock_inv(v):
    """TFP401 clock polarity: None = leave to the pull-up (high), 0 or 1 = force it.
    Try ock_inv(0) if the picture sparkles or the colours are noisy."""
    global ock
    if v is None:
        ock = Pin(9, Pin.IN)
    else:
        ock = Pin(9, Pin.OUT, value=1 if v else 0)


# EDID
def build_edid():
    """128-byte EDID 1.3 with one 800x480 @ 60 Hz mode."""
    e = bytearray(128)
    e[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"
    mfg = "VKR"                                           # 3-letter maker ID
    m = ((ord(mfg[0]) - 64) << 10) | ((ord(mfg[1]) - 64) << 5) | (ord(mfg[2]) - 64)
    e[8], e[9] = m >> 8, m & 0xFF
    e[10], e[11] = PRODUCT_CODE & 0xFF, (PRODUCT_CODE >> 8) & 0xFF   # product code
    e[16], e[17] = 0, 2026 - 1990                         # week (unset), year
    e[18], e[19] = 1, 3                                   # EDID 1.3
    e[20] = 0x80                                          # digital input
    e[21], e[22] = (SCREEN_MM[0] + 5) // 10, (SCREEN_MM[1] + 5) // 10   # size in cm
    e[23] = 120                                           # gamma 2.2
    e[24] = 0x0E                                          # RGB colour, sRGB, first timing is preferred
    e[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])  # sRGB primaries
    for i in range(38, 54):                               # no standard timings
        e[i] = 0x01

    h_blank = H_FP + H_SYNC + H_BP
    v_blank = V_FP + V_SYNC + V_BP
    pclk = (H_ACTIVE + h_blank) * (V_ACTIVE + v_blank) * REFRESH_HZ // 10_000   # units of 10 kHz
    d = bytearray(18)
    d[0], d[1] = pclk & 0xFF, pclk >> 8
    d[2], d[3], d[4] = H_ACTIVE & 0xFF, h_blank & 0xFF, ((H_ACTIVE >> 8) << 4) | (h_blank >> 8)
    d[5], d[6], d[7] = V_ACTIVE & 0xFF, v_blank & 0xFF, ((V_ACTIVE >> 8) << 4) | (v_blank >> 8)
    d[8], d[9] = H_FP & 0xFF, H_SYNC & 0xFF
    d[10] = ((V_FP & 0x0F) << 4) | (V_SYNC & 0x0F)
    d[11] = ((H_FP >> 8) << 6) | ((H_SYNC >> 8) << 4) | ((V_FP >> 4) << 2) | (V_SYNC >> 4)
    d[12], d[13] = SCREEN_MM[0] & 0xFF, SCREEN_MM[1] & 0xFF
    d[14] = ((SCREEN_MM[0] >> 8) << 4) | (SCREEN_MM[1] >> 8)
    d[17] = 0x18                                          # separate sync, HSYNC and VSYNC negative
    e[54:72] = d

    h_khz = pclk * 10 // (H_ACTIVE + h_blank)
    e[72:90] = bytes([0, 0, 0, 0xFD, 0, REFRESH_HZ - 10, REFRESH_HZ + 5, h_khz - 2, h_khz + 3,
                      (pclk // 1000) + 1, 0, 0x0A, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20])   # range limits
    name = MONITOR_NAME.encode()[:13]
    if len(name) < 13:
        name = name + b"\n" + b" " * (12 - len(name))       
    e[90:108] = bytes([0, 0, 0, 0xFC, 0]) + name                                          # name
    e[108:126] = bytes([0, 0, 0, 0x10, 0]) + bytes(13)                                  # unused
    e[126] = 0                                            # no extension blocks
    e[127] = (-sum(e[:127])) & 0xFF
    assert len(e) == 128
    return bytes(e)


EDID = build_edid()


def edid_read():
    return i2c.readfrom_mem(EDID_ADDR, 0, 128)


def edid_check():
    """True if the EEPROM already holds our EDID."""
    try:
        ok = edid_read() == EDID
    except OSError as err:
        print("EEPROM not answering:", err)
        return False
    print("EDID ok" if ok else "EDID different")
    return ok


def edid_write(force=False):
    """Write the EDID 8 bytes at a time (AT24C02 page size), then read it back."""
    if not force and edid_check():
        return True
    edid_we(1)
    time.sleep_ms(2)
    try:
        for a in range(0, 128, 8):
            for attempt in range(5):       # the PC may be reading DDC at the same moment - retry
                try:
                    i2c.writeto_mem(EDID_ADDR, a, EDID[a:a + 8])
                    break
                except OSError:
                    time.sleep_ms(20)
            else:
                print("write failed at byte", a)
                return False
            time.sleep_ms(6)               # EEPROM write cycle (5 ms max)
    finally:
        edid_we(0)
    ok = edid_check()
    if ok:
        print("EDID written - unplug and replug the HDMI cable so the PC reads it again")
    return ok


def edid_dump():
    try:
        b = edid_read()
    except OSError as err:
        print("EEPROM not answering:", err)
        return
    for a in range(0, 128, 16):
        print("%02X: " % a + " ".join("%02X" % x for x in b[a:a + 16]))


def status():
    print("signal (SCDT):", "yes" if scdt() else "no",
          "| backlight:", "on" if _bl_on else "off", "%d %%" % _level,
          "| TFP401:", "on" if tfp_pd() else "powered down")


# main loop
def main():
    print("Cluster2HDMI firmware")
    edid_write()                          # only writes if the EEPROM is blank or different

    have_signal = False
    lost_since = None
    next_group = time.ticks_ms()
    late_due = None

    while True:
        now = time.ticks_ms()
        sig = scdt() == 1

        # video appeared: send the setup straight away, then backlight on
        if sig and not have_signal:
            have_signal = True
            lost_since = None
            time.sleep_ms(SETUP_DELAY_MS)
            send_group()
            late_due = time.ticks_add(time.ticks_ms(), LATE_DELAY_MS)
            next_group = time.ticks_add(time.ticks_ms(), REPEAT_MS)
            print("signal found")

        # video gone: wait SIGNAL_LOST_MS before turning the backlight off (avoids flicker on mode changes)
        if not sig and have_signal:
            if lost_since is None:
                lost_since = now
            elif time.ticks_diff(now, lost_since) > SIGNAL_LOST_MS:
                have_signal = False
                backlight(False)
                print("signal lost - backlight off")
        elif sig:
            lost_since = None

        # repeat the SPI setup like the cluster does
        if time.ticks_diff(now, next_group) >= 0:
            send_group()
            late_due = time.ticks_add(time.ticks_ms(), LATE_DELAY_MS)
            next_group = time.ticks_add(next_group, REPEAT_MS)
        if late_due is not None and time.ticks_diff(time.ticks_ms(), late_due) >= 0:
            spi_write(LATE_CMD)
            late_due = None
            if have_signal and not _bl_on:
                backlight(True)        # first full setup done -> light up

        time.sleep_ms(5)


try:
    main()
except KeyboardInterrupt:
    print("stopped - shell commands still work: brightness(50), status(), edid_dump() ...")
