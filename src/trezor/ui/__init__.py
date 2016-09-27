import math
import utime

from TrezorUi import Display
from trezor import loop


display = Display()


def rgbcolor(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)


LIGHT_RED   = rgbcolor(0xFF, 0x00, 0x00)
RED         = rgbcolor(0x66, 0x00, 0x00)
PINK        = rgbcolor(0xE9, 0x1E, 0x63)
PURPLE      = rgbcolor(0x9C, 0x27, 0xB0)
DEEP_PURPLE = rgbcolor(0x67, 0x3A, 0xB7)
INDIGO      = rgbcolor(0x3F, 0x51, 0xB5)
BLUE        = rgbcolor(0x21, 0x96, 0xF3)
LIGHT_BLUE  = rgbcolor(0x03, 0xA9, 0xF4)
CYAN        = rgbcolor(0x00, 0xBC, 0xD4)
TEAL        = rgbcolor(0x00, 0x96, 0x88)
GREEN       = rgbcolor(0x44, 0x55, 0x14)
LIGHT_GREEN = rgbcolor(0x87, 0xCE, 0x26)
LIME        = rgbcolor(0xCD, 0xDC, 0x39)
YELLOW      = rgbcolor(0xFF, 0xEB, 0x3B)
AMBER       = rgbcolor(0xFF, 0xC1, 0x07)
ORANGE      = rgbcolor(0xFF, 0x98, 0x00)
DEEP_ORANGE = rgbcolor(0xFF, 0x57, 0x22)
BROWN       = rgbcolor(0x79, 0x55, 0x48)
LIGHT_GREY  = rgbcolor(0xDA, 0xDD, 0xD8)
GREY        = rgbcolor(0x9E, 0x9E, 0x9E)
DARK_GREY   = rgbcolor(0x3E, 0x3E, 0x3E)
BLUE_GRAY   = rgbcolor(0x60, 0x7D, 0x8B)
BLACK       = rgbcolor(0x00, 0x00, 0x00)
WHITE       = rgbcolor(0xFA, 0xFA, 0xFA)

# password manager palette

PM_DARK_BLUE = rgbcolor(0x1A, 0x29, 0x42)
PM_BLUE      = rgbcolor(0x34, 0x98, 0xdb)

MONO   = const(0)
NORMAL = const(1)
BOLD   = const(2)


def clear(color=BLACK):
    display.bar(0, 0, 240, 240, color)


def in_area(pos: tuple, area: tuple) -> bool:
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


def rotate_coords(pos: tuple) -> tuple:
    r = display.orientation()
    if r == 0:
        return pos
    x, y = pos
    if r == 90:
        return (y, 240 - x)
    if r == 180:
        return (240 - x, 240 - y)
    if r == 270:
        return (240 - y, x)
