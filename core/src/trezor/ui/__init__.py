# pylint: disable=wrong-import-position
import math
import utime
from micropython import const
from trezorui import Display

from trezor import io, loop, res, utils, workflow

if False:
    from typing import Any, Awaitable, Generator, TypeVar

    Pos = tuple[int, int]
    Area = tuple[int, int, int, int]
    ResultValue = TypeVar("ResultValue")

# all rendering is done through a singleton of `Display`
display = Display()

# re-export constants from modtrezorui
NORMAL = Display.FONT_NORMAL
BOLD = Display.FONT_BOLD
MONO = Display.FONT_MONO
WIDTH = Display.WIDTH
HEIGHT = Display.HEIGHT

# viewport margins
VIEWX = const(6)
VIEWY = const(9)

# channel used to cancel layouts, see `Cancelled` exception
layout_chan = loop.chan()

# allow only one alert at a time to avoid alerts overlapping
_alert_in_progress = False

# in debug mode, display an indicator in top right corner
if __debug__:

    def refresh() -> None:
        from apps.debug import screenshot

        if not screenshot():
            display.bar(Display.WIDTH - 8, 0, 8, 8, 0xF800)
        display.refresh()


else:
    refresh = display.refresh


# in both debug and production, emulator needs to draw the screen explicitly
if utils.EMULATOR or utils.MODEL == "1":
    loop.after_step_hook = refresh


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


def pulse(period: int, offset: int = 0) -> float:
    # normalize sin from interval -1:1 to 0:1
    return 0.5 + 0.5 * math.sin(2 * math.pi * (utime.ticks_us() + offset) / period)


async def _alert(count: int) -> None:
    short_sleep = loop.sleep(20)
    long_sleep = loop.sleep(80)
    for i in range(count * 2):
        if i % 2 == 0:
            display.backlight(style.BACKLIGHT_MAX)
            await short_sleep
        else:
            display.backlight(style.BACKLIGHT_DIM)
            await long_sleep
    display.backlight(style.BACKLIGHT_NORMAL)
    global _alert_in_progress
    _alert_in_progress = False


def alert(count: int = 3) -> None:
    global _alert_in_progress
    if _alert_in_progress:
        return

    _alert_in_progress = True
    loop.schedule(_alert(count))


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
        if utils.DISABLE_ANIMATION:
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


def header_warning(message: str, clear: bool = True) -> None:
    display.bar(0, 0, WIDTH, 30, style.YELLOW)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.BLACK, style.YELLOW)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def header_error(message: str, clear: bool = True) -> None:
    display.bar(0, 0, WIDTH, 30, style.RED)
    display.text_center(WIDTH // 2, 22, message, BOLD, style.WHITE, style.RED)
    if clear:
        display.bar(0, 30, WIDTH, HEIGHT - 30, style.BG)


def draw_simple(t: "Component") -> None:
    """Render a component synchronously.

    Useful when you need to put something on screen and go on to do other things.

    This function bypasses the UI workflow engine, so other layouts will not know
    that something was drawn over them. In particular, if no other Layout is shown
    in a workflow, the homescreen will not redraw when the workflow is finished.
    Make sure you use `workflow.close_others()` before invoking this function
    (note that `workflow.close_others()` is implicitly called with `button_request()`).
    """
    backlight_fade(style.BACKLIGHT_DIM)
    display.clear()
    t.on_render()
    refresh()
    backlight_fade(style.BACKLIGHT_NORMAL)


def grid(
    i: int,  # i-th cell of the table of which we wish to return Area (snake-like starting with 0)
    n_x: int = 3,  # number of rows in the table
    n_y: int = 5,  # number of columns in the table
    start_x: int = VIEWX,  # where the table starts on x-axis
    start_y: int = VIEWY,  # where the table starts on y-axis
    end_x: int = (WIDTH - VIEWX),  # where the table ends on x-axis
    end_y: int = (HEIGHT - VIEWY),  # where the table ends on y-axis
    cells_x: int = 1,  # number of cells to be merged into one in the direction of x-axis
    cells_y: int = 1,  # number of cells to be merged into one in the direction of y-axis
    spacing: int = 0,  # spacing size between cells
) -> Area:
    """
    Returns area (tuple of four integers, in pixels) of a cell on i-th position
    in a table you define yourself.  Example:

    >>> ui.grid(4, n_x=2, n_y=3, start_x=20, start_y=20)
    (20, 160, 107, 70)

    Returns 5th cell from the following table.  It has two columns, three rows
    and starts on coordinates 20-20.

        |____|____|
        |____|____|
        |XXXX|____|
    """
    w = (end_x - start_x) // n_x
    h = (end_y - start_y) // n_y
    x = (i % n_x) * w
    y = (i // n_x) * h
    return (x + start_x, y + start_y, (w - spacing) * cells_x, (h - spacing) * cells_y)


def in_area(area: Area, x: int, y: int) -> bool:
    ax, ay, aw, ah = area
    return ax <= x < ax + aw and ay <= y < ay + ah


# Component events.  Should be different from `io.TOUCH_*` events.
# Event dispatched when components should draw to the display, if they are
# marked for re-paint.
RENDER = const(-255)
# Event dispatched when components should mark themselves for re-painting.
REPAINT = const(-256)

# How long, in milliseconds, should the layout rendering task sleep between
# the render calls.
_RENDER_DELAY_MS = const(10)


class Component:
    """
    Abstract class.

    Components are GUI classes that inherit `Component` and form a tree, with a
    `Layout` at the root, and other components underneath.  Components that
    have children, and therefore need to dispatch events to them, usually
    override the `dispatch` method.  Leaf components usually override the event
    methods (`on_*`).  Components signal a completion to the layout by raising
    an instance of `Result`.
    """

    def __init__(self) -> None:
        self.repaint = True

    if utils.MODEL == "T":

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

        def on_touch_start(self, x: int, y: int) -> None:
            pass

        def on_touch_move(self, x: int, y: int) -> None:
            pass

        def on_touch_end(self, x: int, y: int) -> None:
            pass

    elif utils.MODEL == "1":

        def dispatch(self, event: int, x: int, y: int) -> None:
            if event is RENDER:
                self.on_render()
            elif event is io.BUTTON_PRESSED:
                self.on_button_pressed(x)
            elif event is io.BUTTON_RELEASED:
                self.on_button_released(x)
            elif event is REPAINT:
                self.repaint = True

        def on_button_pressed(self, button_number: int) -> None:
            pass

        def on_button_released(self, button_number: int) -> None:
            pass

    def on_render(self) -> None:
        pass

    if __debug__:

        def read_content(self) -> list[str]:
            return [self.__class__.__name__]


class Result(Exception):
    """
    When components want to trigger layout completion, they do so through
    raising an instance of `Result`.

    See `Layout.__iter__` for details.
    """

    def __init__(self, value: ResultValue) -> None:
        super().__init__()
        self.value = value


class Cancelled(Exception):
    """
    Layouts can be explicitly cancelled.  This usually happens when another
    layout starts, because only one layout can be running at the same time,
    and is done by raising `Cancelled` on the cancelled layout.  Layouts
    should always re-raise such exceptions.

    See `Layout.__iter__` for details.
    """


class Layout(Component):
    """
    Abstract class.

    Layouts are top-level components.  Only one layout can be running at the
    same time.  Layouts provide asynchronous interface, so a running task can
    wait for the layout to complete.  Layouts complete when a `Result` is
    raised, usually from some of the child components.
    """

    BACKLIGHT_LEVEL = style.BACKLIGHT_NORMAL
    RENDER_SLEEP: loop.Syscall = loop.sleep(_RENDER_DELAY_MS)

    async def __iter__(self) -> ResultValue:
        """
        Run the layout and wait until it completes.  Returns the result value.
        Usually not overridden.
        """
        if __debug__:
            # we want to call notify_layout_change() when the rendering is done;
            # but only the first time the layout is awaited. Here we indicate that we
            # are being awaited, and in handle_rendering() we send the appropriate event
            self.should_notify_layout_change = True

        value = None
        try:
            # If any other layout is running (waiting on the layout channel),
            # we close it with the Cancelled exception, and wait until it is
            # closed, just to be sure.
            if layout_chan.takers:
                await layout_chan.put(Cancelled())
            # Now, no other layout should be running.  In a loop, we create new
            # layout tasks and execute them in parallel, while waiting on the
            # layout channel.  This allows other layouts to cancel us, and the
            # layout tasks to trigger restart by exiting (new tasks are created
            # and we continue, because we are in a loop).
            while True:
                await loop.race(layout_chan.take(), *self.create_tasks())
        except Result as result:
            # Result exception was raised, this means this layout is complete.
            value = result.value
        return value

    def __await__(self) -> Generator[Any, Any, ResultValue]:
        return self.__iter__()  # type: ignore

    def create_tasks(self) -> tuple[loop.Task, ...]:
        """
        Called from `__iter__`.  Creates and returns a sequence of tasks that
        run this layout.  Tasks are executed in parallel.  When one of them
        returns, the others are closed and `create_tasks` is called again.

        Usually overridden to add another tasks to the list."""
        return self.handle_input(), self.handle_rendering()

    if utils.MODEL == "T":

        def handle_input(self) -> loop.Task:  # type: ignore
            """Task that is waiting for the user input."""
            touch = loop.wait(io.TOUCH)
            while True:
                # Using `yield` instead of `await` to avoid allocations.
                event, x, y = yield touch
                workflow.idle_timer.touch()
                self.dispatch(event, x, y)
                # We dispatch a render event right after the touch.  Quick and dirty
                # way to get the lowest input-to-render latency.
                self.dispatch(RENDER, 0, 0)

    elif utils.MODEL == "1":

        def handle_input(self) -> loop.Task:  # type: ignore
            """Task that is waiting for the user input."""
            button = loop.wait(io.BUTTON)
            while True:
                event, button_num = yield button
                workflow.idle_timer.touch()
                self.dispatch(event, button_num, 0)
                self.dispatch(RENDER, 0, 0)

    else:
        raise ValueError("Unknown Trezor model")

    def _before_render(self) -> None:
        # Before the first render, we dim the display.
        backlight_fade(style.BACKLIGHT_DIM)
        # Clear the screen of any leftovers, make sure everything is marked for
        # repaint (we can be running the same layout instance multiple times)
        # and paint it.
        display.clear()
        self.dispatch(REPAINT, 0, 0)
        self.dispatch(RENDER, 0, 0)

        if __debug__ and self.should_notify_layout_change:
            from apps.debug import notify_layout_change

            # notify about change and do not notify again until next await.
            # (handle_rendering might be called multiple times in a single await,
            # because of the endless loop in __iter__)
            self.should_notify_layout_change = False
            notify_layout_change(self)

        # Display is usually refreshed after every loop step, but here we are
        # rendering everything synchronously, so refresh it manually and turn
        # the brightness on again.
        refresh()
        backlight_fade(self.BACKLIGHT_LEVEL)

    def handle_rendering(self) -> loop.Task:  # type: ignore
        """Task that is rendering the layout in a busy loop."""
        self._before_render()
        sleep = self.RENDER_SLEEP
        while True:
            # Wait for a couple of ms and render the layout again.  Because
            # components use re-paint marking, they do not really draw on the
            # display needlessly.  Using `yield` instead of `await` to avoid allocations.
            # TODO: remove the busy loop
            yield sleep
            self.dispatch(RENDER, 0, 0)


def wait_until_layout_is_running() -> Awaitable[None]:  # type: ignore
    while not layout_chan.takers:
        yield


if utils.MODEL == "1":

    class RustLayout(Layout):
        def __init__(self, layout: Any):
            super().__init__()
            self.layout = layout
            self.layout.set_timer_fn(self.set_timer)

        def set_timer(self, token: int, deadline: int) -> None:
            # TODO: schedule a timer tick with `token` in `deadline` ms
            print("timer", token, deadline)

        def dispatch(self, event: int, x: int, y: int) -> None:
            msg = None
            if event is RENDER:
                self.layout.paint()
            elif event in (io.BUTTON_PRESSED, io.BUTTON_RELEASED):
                msg = self.layout.hid_event(event, x, 0)
            # elif event in (io.TOUCH_START, io.TOUCH_MOVE, io.TOUCH_END):
            #    self.layout.hid_event(event, x, y)
            if msg is not None:
                raise Result(msg)
