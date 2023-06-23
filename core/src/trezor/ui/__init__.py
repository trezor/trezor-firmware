# pylint: disable=wrong-import-position
import utime
from micropython import const
from trezorui import Display
from typing import TYPE_CHECKING, Any, Awaitable, Generator

from trezor import io, loop, utils, workflow

# all rendering is done through a singleton of `Display`
display = Display()

# re-export constants from modtrezorui
NORMAL: int = Display.FONT_NORMAL
BOLD: int = Display.FONT_BOLD
DEMIBOLD: int = Display.FONT_DEMIBOLD
MONO: int = Display.FONT_MONO
WIDTH: int = Display.WIDTH
HEIGHT: int = Display.HEIGHT

# channel used to cancel layouts, see `Cancelled` exception
layout_chan = loop.chan()

# allow only one alert at a time to avoid alerts overlapping
_alert_in_progress = False

# in debug mode, display an indicator in top right corner
if __debug__:

    def refresh() -> None:
        from apps.debug import screenshot

        if not screenshot():
            side = Display.WIDTH // 30
            display.bar(Display.WIDTH - side, 0, side, side, 0xF800)
        display.refresh()

else:
    refresh = display.refresh  # type: ignore [obscured-by-same-name]


# in both debug and production, emulator needs to draw the screen explicitly
if utils.EMULATOR or utils.MODEL in ("1", "R"):
    loop.after_step_hook = refresh


# import style later to avoid circular dep
from trezor.ui import style  # isort:skip

# import style definitions into namespace
from trezor.ui.style import *  # isort:skip # noqa: F401,F403


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
    if utils.USE_BACKLIGHT:
        global _alert_in_progress
        if _alert_in_progress:
            return

        _alert_in_progress = True
        loop.schedule(_alert(count))


def backlight_fade(val: int, delay: int = 14000, step: int = 15) -> None:
    if utils.USE_BACKLIGHT:
        if __debug__:
            if utils.DISABLE_ANIMATION:
                display.backlight(val)
                return
        current = display.backlight()
        if current < 0:
            display.backlight(val)
            return
        elif current > val:
            step = -step
        for i in range(current, val, step):
            display.backlight(i)
            utime.sleep_us(delay)
        display.backlight(val)


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

    if utils.MODEL in ("T", "DISC1"):

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

    elif utils.MODEL in ("1", "R"):

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

        def read_content_into(self, content_store: list[str]) -> None:
            content_store.clear()
            content_store.append(self.__class__.__name__)


class Result(Exception):
    """
    When components want to trigger layout completion, they do so through
    raising an instance of `Result`.

    See `Layout.__iter__` for details.
    """

    def __init__(self, value: Any) -> None:
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

    async def __iter__(self) -> Any:
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

    if TYPE_CHECKING:

        def __await__(self) -> Generator:
            return self.__iter__()  # type: ignore [Expression of type "Coroutine[Any, Any, Any]" cannot be assigned to return type "Generator[Unknown, Unknown, Unknown]"]

    else:
        __await__ = __iter__

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        """
        Called from `__iter__`.  Creates and returns a sequence of tasks that
        run this layout.  Tasks are executed in parallel.  When one of them
        returns, the others are closed and `create_tasks` is called again.

        Usually overridden to add another tasks to the list."""
        return self.handle_input(), self.handle_rendering()

    if utils.MODEL in ("T", "DISC1"):

        def handle_input(self) -> Generator:
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

    elif utils.MODEL in ("1", "R"):

        def handle_input(self) -> Generator:
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
        backlight_fade(style.BACKLIGHT_NONE)
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

    def handle_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
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


def wait_until_layout_is_running() -> Awaitable[None]:  # type: ignore [awaitable-is-generator]
    while not layout_chan.takers:
        yield
