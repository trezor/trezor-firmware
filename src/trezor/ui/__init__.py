import math
import utime

from TrezorUi import Display
from trezor import loop


display = Display()


def rgbcolor(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)


RED         = rgbcolor(0xF4, 0x43, 0x36)
PINK        = rgbcolor(0xE9, 0x1E, 0x63)
PURPLE      = rgbcolor(0x9C, 0x27, 0xB0)
DEEP_PURPLE = rgbcolor(0x67, 0x3A, 0xB7)
INDIGO      = rgbcolor(0x3F, 0x51, 0xB5)
BLUE        = rgbcolor(0x21, 0x96, 0xF3)
LIGHT_BLUE  = rgbcolor(0x03, 0xA9, 0xF4)
CYAN        = rgbcolor(0x00, 0xBC, 0xD4)
TEAL        = rgbcolor(0x00, 0x96, 0x88)
GREEN       = rgbcolor(0x4C, 0xAF, 0x50)
LIGHT_GREEN = rgbcolor(0x8B, 0xC3, 0x4A)
LIME        = rgbcolor(0xCD, 0xDC, 0x39)
YELLOW      = rgbcolor(0xFF, 0xEB, 0x3B)
AMBER       = rgbcolor(0xFF, 0xC1, 0x07)
ORANGE      = rgbcolor(0xFF, 0x98, 0x00)
DEEP_ORANGE = rgbcolor(0xFF, 0x57, 0x22)
BROWN       = rgbcolor(0x79, 0x55, 0x48)
GREY        = rgbcolor(0x9E, 0x9E, 0x9E)
BLUE_GRAY   = rgbcolor(0x60, 0x7D, 0x8B)
BLACK       = rgbcolor(0x00, 0x00, 0x00)
WHITE       = rgbcolor(0xFF, 0xFF, 0xFF)

MONO   = const(0)
NORMAL = const(1)
BOLD   = const(2)


def in_area(pos, area):
    x, y = pos
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


def lerpi(a: int, b: int, t: float) -> int:
    return int(a + t * (b - a))


def blend(ca: int, cb: int, t: float) -> int:
    return rgbcolor(lerpi((ca >> 8) & 0xF8, (cb >> 8) & 0xF8, t),
                    lerpi((ca >> 3) & 0xFC, (cb >> 3) & 0xFC, t),
                    lerpi((ca << 3) & 0xF8, (cb << 3) & 0xF8, t))


def animate_pulse(func, ca, cb, speed=200000, delay=30000):
    while True:
        # normalize sin from interval -1:1 to 0:1
        y = 0.5 + 0.5 * math.sin(utime.ticks_us() / speed)
        c = blend(ca, cb, y)
        func(c)
        yield loop.Sleep(delay)
