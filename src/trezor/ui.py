import math
import utime

from TrezorUi import Display, Touch

from . import loop

display = Display()
touch = Touch()

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


def animate_pulse(func, SPEED=200000, DELAY=30000, BASE_COLOR=(0x00, 0x00, 0x00), MIN_COLOR=0x00, MAX_COLOR=0x80):
    while True:
        y = 1 + math.sin(utime.ticks_us() / SPEED)

        # Normalize color from interval 0:2 to MIN_COLOR:MAX_COLOR
        col = int((MAX_COLOR - MIN_COLOR) / 2 * y) + MIN_COLOR
        foreground = rgbcolor(BASE_COLOR[0] + col, BASE_COLOR[1] + col, BASE_COLOR[2] + col)

        func(foreground)
        yield loop.Sleep(DELAY)

