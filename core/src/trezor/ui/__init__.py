import math
import utime
from micropython import const
from trezorui import Display

from trezor import io, loop, res, utils, workflow

if False:
    from typing import Any, Generator, Iterable, Tuple, TypeVar

    Pos = Tuple[int, int]
    Area = Tuple[int, int, int, int]

display = Display()

# in debug mode, display an indicator in top right corner
if __debug__:

    def debug_display_refresh() -> None:
        display.bar(Display.WIDTH - 8, 0, 8, 8, 0xF800)
        display.refresh()
        if utils.SAVE_SCREEN:
            display.save("refresh")

    loop.after_step_hook = debug_display_refresh

# in both debug and production, emulator needs to draw the screen explicitly
elif utils.EMULATOR:
    loop.after_step_hook = display.refresh

# re-export constants from modtrezorui
NORMAL = Display.FONT_NORMAL
BOLD = Display.FONT_BOLD
MONO = Display.FONT_MONO
MONO_BOLD = Display.FONT_MONO_BOLD
SIZE = Display.FONT_SIZE
WIDTH = Display.WIDTH
HEIGHT = Display.HEIGHT

# viewport margins
VIEWX = const(6)
VIEWY = const(9)


def lerpi(a: int, b: int, t: float) -> int:
    return int(a + t * (b - a))


def rgb(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)


def blend(ca: int, cb: int, t: float) -> int:
    return rgb(
        lerpi((ca >> 8) & 0xF8, (cb >> 8) & 0xF8, t),
        lerpi((ca >> 3) & 0xFC, (cb >> 3) & 0xFC, t),
        lerpi((ca << 3) & 0xF8, (cb << 3) & 0xF8, t),
    )


# import style later to avoid circular dep
from trezor.ui import style  # isort:skip

# import style definitions into namespace
from trezor.ui.style import *  # isort:skip # noqa: F401,F403


def pulse(delay: int) -> float:
    # normalize sin from interval -1:1 to 0:1
    return 0.5 + 0.5 * math.sin(utime.ticks_us() / delay)


async def click() -> Pos:
    touch = loop.wait(io.TOUCH)
    while True:
        ev, *pos = await touch
        if ev == io.TOUCH_START:
            break
    while True:
        ev, *pos = await touch
        if ev == io.TOUCH_END:
            break
    return pos  # type: ignore


def backlight_fade(val: int, delay: int = 14000, step: int = 15) -> None:
    if __debug__:
        if utils.DISABLE_FADE:
            display.backlight(val)
            return
    current = display.backlight()
    if current > val:
        step = -step
    for i in range(current, val, step):
        display.backlight(i)
        utime.sleep_us(delay)


def header(
    title: str,
    icon: str = style.ICON_DEFAULT,
    fg: int = style.FG,
    bg: int = style.BG,
    ifg: int = style.GREEN,
) -> None:
    if icon is not None:
        display.icon(14, 15, res.load(icon), ifg, bg)
    display.text(44, 35, title, BOLD, fg, bg)


def header_warning(message: str, clear=True) -> None:
    # TODO: review: is the clear=True really needed?
    display.bar(0, 0, WIDTH, 30, style.YELLOW)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.BLACK, style.YELLOW)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def header_error(message: str, clear=True) -> None:
    # TODO: review: as above
    display.bar(0, 0, WIDTH, 30, style.RED)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.WHITE, style.RED)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def grid(
    i: int,
    n_x: int = 3,
    n_y: int = 5,
    start_x: int = VIEWX,
    start_y: int = VIEWY,
    end_x: int = (WIDTH - VIEWX),
    end_y: int = (HEIGHT - VIEWY),
    cells_x: int = 1,
    cells_y: int = 1,
    spacing: int = 0,
) -> Area:
    w = (end_x - start_x) // n_x
    h = (end_y - start_y) // n_y
    x = (i % n_x) * w
    y = (i // n_x) * h
    return (x + start_x, y + start_y, (w - spacing) * cells_x, (h - spacing) * cells_y)


def in_area(area: Area, x: int, y: int) -> bool:
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


# render events
RENDER = const(-255)
REPAINT = const(-256)


class Control:
    def dispatch(self, event: int, x: int, y: int) -> None:
        if event is RENDER:
            self.on_render()
        elif event is io.TOUCH_START:
            self.on_touch_start(x, y)
        elif event is io.TOUCH_MOVE:
            self.on_touch_move(x, y)
        elif event is io.TOUCH_END:
            self.on_touch_end(x, y)
        elif event is REPAINT:
            self.repaint = True

    def on_render(self) -> None:
        pass

    def on_touch_start(self, x: int, y: int) -> None:
        pass

    def on_touch_move(self, x: int, y: int) -> None:
        pass

    def on_touch_end(self, x: int, y: int) -> None:
        pass


_RENDER_DELAY_US = const(10000)  # 10 msec


class LayoutCancelled(Exception):
    pass


if False:
    ResultValue = TypeVar("ResultValue")


class Result(Exception):
    def __init__(self, value: ResultValue) -> None:
        self.value = value


class Layout(Control):
    """
    """

    async def __iter__(self) -> ResultValue:
        value = None
        try:
            if workflow.layout_signal.task is not None:
                workflow.layout_signal.send(LayoutCancelled())
            workflow.onlayoutstart(self)
            while True:
                layout_tasks = self.create_tasks()
                await loop.spawn(workflow.layout_signal, *layout_tasks)
        except Result as result:
            value = result.value
        finally:
            workflow.onlayoutclose(self)
        return value

    def __await__(self) -> Generator[Any, Any, ResultValue]:
        return self.__iter__()  # type: ignore

    def create_tasks(self) -> Iterable[loop.Task]:
        return self.handle_input(), self.handle_rendering()

    def handle_input(self) -> loop.Task:  # type: ignore
        touch = loop.wait(io.TOUCH)
        while True:
            event, x, y = yield touch
            self.dispatch(event, x, y)
            self.dispatch(RENDER, 0, 0)

    def handle_rendering(self) -> loop.Task:  # type: ignore
        backlight_fade(style.BACKLIGHT_DIM)
        display.clear()
        self.dispatch(RENDER, 0, 0)
        display.refresh()
        backlight_fade(style.BACKLIGHT_NORMAL)
        sleep = loop.sleep(_RENDER_DELAY_US)
        while True:
            self.dispatch(RENDER, 0, 0)
            yield sleep
