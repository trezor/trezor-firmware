# pylint: disable=wrong-import-position
import utime
from trezorui import Display
from typing import TYPE_CHECKING, Any, Awaitable, Generator

from trezor import loop, utils
from trezorui2 import AttachType, BacklightLevels

if TYPE_CHECKING:
    from typing import Generic, TypeVar

    from trezorui2 import UiResult  # noqa: F401

    T = TypeVar("T")

else:
    Generic = [object]
    T = 0

# all rendering is done through a singleton of `Display`
display = Display()

# re-export constants from modtrezorui
NORMAL: int = Display.FONT_NORMAL
DEMIBOLD: int = Display.FONT_DEMIBOLD
BOLD_UPPER: int = Display.FONT_BOLD_UPPER
MONO: int = Display.FONT_MONO
WIDTH: int = Display.WIDTH
HEIGHT: int = Display.HEIGHT

# channel used to cancel layouts, see `Cancelled` exception
layout_chan = loop.chan()

# allow only one alert at a time to avoid alerts overlapping
_alert_in_progress = False

# storing last transition type, so that next layout can continue nicely
LAST_TRANSITION_OUT: AttachType | None = None

# in debug mode, display an indicator in top right corner
if __debug__:

    def refresh() -> None:
        from apps.debug import screenshot

        if not screenshot():
            side = Display.WIDTH // 30
            display.bar(Display.WIDTH - side, 0, side, side, 0xF800)
        display.refresh()

else:
    refresh = display.refresh


# in both debug and production, emulator needs to draw the screen explicitly
if utils.EMULATOR or utils.INTERNAL_MODEL == "T2B1" or utils.INTERNAL_MODEL == "T3B1":
    loop.after_step_hook = refresh


async def _alert(count: int) -> None:
    short_sleep = loop.sleep(20)
    long_sleep = loop.sleep(80)
    for i in range(count * 2):
        if i % 2 == 0:
            display.backlight(BacklightLevels.MAX)
            await short_sleep
        else:
            display.backlight(BacklightLevels.DIM)
            await long_sleep
    display.backlight(BacklightLevels.NORMAL)
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


class Layout(Generic[T]):
    """
    Abstract class.

    Layouts are top-level components.  Only one layout can be running at the
    same time.  Layouts provide asynchronous interface, so a running task can
    wait for the layout to complete.  Layouts complete when a `Result` is
    raised, usually from some of the child components.
    """

    def finalize(self) -> None:
        """
        Called when the layout is done. Usually overridden to allow cleanup or storing context.
        """
        pass

    async def __iter__(self) -> T:
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
        finally:
            self.finalize()
        return value

    if TYPE_CHECKING:

        def __await__(self) -> Generator[Any, Any, T]:
            return self.__iter__()  # type: ignore [Coroutine[Any, Any, T@Layout]" is incompatible with "Generator[Any, Any, T@Layout]"]

    else:
        __await__ = __iter__

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        """
        Called from `__iter__`.  Creates and returns a sequence of tasks that
        run this layout.  Tasks are executed in parallel.  When one of them
        returns, the others are closed and `create_tasks` is called again.

        Usually overridden to add another tasks to the list."""
        raise NotImplementedError

    if __debug__:

        def read_content_into(self, content_store: list[str]) -> None:
            content_store.clear()
            content_store.append(self.__class__.__name__)


def wait_until_layout_is_running() -> Awaitable[None]:  # type: ignore [awaitable-return-type]
    while not layout_chan.takers:
        yield  # type: ignore [awaitable-return-type]
