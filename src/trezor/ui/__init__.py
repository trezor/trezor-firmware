from micropython import const

import sys
import math
import utime

from trezorui import Display

from trezor import io
from trezor import loop
from trezor import res

display = Display()

# for desktop platforms, we need to refresh the display after each frame
if sys.platform != 'trezor':
    loop.after_step_hook = display.refresh

# font styles
NORMAL = Display.FONT_NORMAL
BOLD = Display.FONT_BOLD
MONO = Display.FONT_MONO

# display width and height
SCREEN = const(240)


def lerpi(a: int, b: int, t: float) -> int:
    return int(a + t * (b - a))


def rgb(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)


def blend(ca: int, cb: int, t: float) -> int:
    return rgb(
        lerpi((ca >> 8) & 0xF8, (cb >> 8) & 0xF8, t),
        lerpi((ca >> 3) & 0xFC, (cb >> 3) & 0xFC, t),
        lerpi((ca << 3) & 0xF8, (cb << 3) & 0xF8, t))


from trezor.ui.style import *


def contains(area: tuple, pos: tuple) -> bool:
    x, y = pos
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


def rotate(pos: tuple) -> tuple:
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


def pulse(delay: int):
    while True:
        # normalize sin from interval -1:1 to 0:1
        yield 0.5 + 0.5 * math.sin(utime.ticks_us() / delay)


async def alert(count: int=3):
    short_sleep = loop.sleep(20000)
    long_sleep = loop.sleep(80000)
    current = display.backlight()
    for i in range(count * 2):
        if i % 2 == 0:
            display.backlight(BACKLIGHT_MAX)
            yield short_sleep
        else:
            display.backlight(BACKLIGHT_NORMAL)
            yield long_sleep
    display.backlight(current)


async def backlight_slide(val: int, delay: int=20000):
    sleep = loop.sleep(delay)
    current = display.backlight()
    for i in range(current, val, -1 if current > val else 1):
        display.backlight(i)
        await sleep


def layout(f):
    async def inner(*args, **kwargs):
        slider = backlight_slide(BACKLIGHT_NORMAL, 4000)
        loop.schedule(slider)
        await f(*args, **kwargs)
        slider.close()
        await backlight_slide(BACKLIGHT_DIM, 4000)

    return inner


def header(title: str, icon: bytes=ICON_RESET, fg: int=BG, bg: int=BG):
    display.bar(0, 0, 240, 32, bg)
    if icon is not None:
        display.icon(8, 4, res.load(icon), fg, bg)
    display.text(8 + 24 + 2, 24, title, BOLD, fg, bg)


class Widget:
    def render(self):
        pass

    def touch(self, event, pos):
        pass

    def __iter__(self):
        touch = loop.select(io.TOUCH)
        result = None
        while result is None:
            self.render()
            event, *pos = yield touch
            result = self.touch(event, pos)
        return result
