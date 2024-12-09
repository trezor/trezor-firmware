# pylint: disable=wrong-import-position
import utime
from micropython import const
from trezorui import Display
from typing import TYPE_CHECKING

from trezor import io, log, loop, utils, wire, workflow
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import context
from trezor.wire.protocol_common import Context
from trezorui_api import AttachType, BacklightLevels, LayoutState

if TYPE_CHECKING:
    from typing import Any, Callable, Generator, Generic, Iterator, TypeVar

    from trezorui_api import LayoutObj, UiResult  # noqa: F401

    T = TypeVar("T", covariant=True)

else:
    T = 0
    Generic = {T: object}


if __debug__:
    from trezorui_api import disable_animation

    disable_animation(utils.DISABLE_ANIMATION)


# all rendering is done through a singleton of `Display`
display = Display()

# re-export constants from modtrezorui
NORMAL: int = Display.FONT_NORMAL
DEMIBOLD: int = Display.FONT_DEMIBOLD
BOLD_UPPER: int = Display.FONT_BOLD_UPPER
MONO: int = Display.FONT_MONO
WIDTH: int = Display.WIDTH
HEIGHT: int = Display.HEIGHT

_REQUEST_ANIMATION_FRAME = const(1)
"""Animation frame timer token.
See `trezor::ui::layout::base::EventCtx::ANIM_FRAME_TIMER`.
"""

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
    refresh = display.refresh


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


class Shutdown(Exception):
    pass


SHUTDOWN = Shutdown()

CURRENT_LAYOUT: "Layout | ProgressLayout | None" = None


def set_current_layout(layout: "Layout | ProgressLayout | None") -> None:
    """Set the current global layout.

    All manipulation of the global `CURRENT_LAYOUT` MUST go through this function.
    It ensures that the transitions are always to/from None (so that there are never
    two layouts in RUNNING state), and that the debug UI is notified of the change.
    """
    global CURRENT_LAYOUT

    # all transitions must be to/from None
    assert (CURRENT_LAYOUT is None) == (layout is not None)

    CURRENT_LAYOUT = layout


class Layout(Generic[T]):
    """Python-side handler and runner for the Rust based layouts.

    Wrap a `LayoutObj` instance in `Layout` to be able to display the layout, run its
    event loop, and take part in global layout management. See
    [docs/core/misc/layout-lifecycle.md] for details.
    """

    if __debug__:

        @staticmethod
        def _trace(layout: LayoutObj) -> str:
            tokens = []

            def callback(*args: str) -> None:
                tokens.extend(args)

            layout.trace(callback)
            return "".join(tokens)

        def __str__(self) -> str:
            return f"{repr(self)}({self._trace(self.layout)[:150]})"

        @staticmethod
        def notify_debuglink(layout: "Layout | None") -> None:
            from apps.debug import notify_layout_change

            notify_layout_change(layout)

    def __init__(self, layout: LayoutObj[T]) -> None:
        """Set up a layout."""
        self.layout = layout
        self.tasks: set[loop.Task] = set()
        self.timers: dict[int, loop.Task] = {}
        self.result_box = loop.mailbox()
        self.button_request_box = loop.mailbox()
        self.button_request_ack_pending: bool = False
        self.transition_out: AttachType | None = None
        self.backlight_level = BacklightLevels.NORMAL
        self.context: Context | None = None
        self.state: LayoutState = LayoutState.INITIAL

        # Indicates whether we should use Resume attach style when launching.
        # Homescreen layouts can override this.
        self.should_resume = False

    def is_ready(self) -> bool:
        """True if the layout is in READY state."""
        return CURRENT_LAYOUT is not self and self.result_box.is_empty()

    def is_running(self) -> bool:
        """True if the layout is in RUNNING state."""
        return CURRENT_LAYOUT is self

    def is_finished(self) -> bool:
        """True if the layout is in FINISHED state."""
        return CURRENT_LAYOUT is not self and not self.result_box.is_empty()

    def is_layout_attached(self) -> bool:
        return self.state is LayoutState.ATTACHED

    def start(self) -> None:
        """Start the layout, stopping any other RUNNING layout.

        If the layout is already RUNNING, do nothing. If the layout is FINISHED, fail.
        """
        global CURRENT_LAYOUT

        # do nothing if we are already running
        if self.is_running():
            return

        # make sure we are not restarted before picking the previous result
        assert self.is_ready()

        transition_in = AttachType.RESUME if self.should_resume else AttachType.INITIAL

        # set up the global layout, shutting down any competitors
        # (caller should still call `workflow.close_others()` to ensure that someone
        # else will not just shut us down immediately)
        if CURRENT_LAYOUT is not None:
            prev_layout = CURRENT_LAYOUT
            prev_layout.stop()
            transition_in = prev_layout.transition_out

        assert CURRENT_LAYOUT is None
        # do not notify debuglink, we will do it when we receive an ATTACHED event
        set_current_layout(self)

        # save context
        self.context = context.CURRENT_CONTEXT

        # attach a timer callback and paint self
        self._event(self.layout.attach_timer_fn, self._set_timer, transition_in)

        # spawn all tasks
        for task in self.create_tasks():
            self._start_task(task)

    def stop(self, _kill_taker: bool = True) -> None:
        """Stop the layout, moving out of RUNNING state and unsetting self as the
        current layout.

        The resulting state is either READY (if there is no result to be picked up) or
        FINISHED.

        When called externally, this kills any tasks that wait for the result, assuming
        that the external `stop()` is a kill. When called internally, `_kill_taker` is
        set to False to indicate that a result became available and that the taker
        should be allowed to pick it up.
        """
        global CURRENT_LAYOUT

        # stop all running timers and spawned tasks
        for timer in self.timers.values():
            loop.close(timer)
        for task in self.tasks:
            if task != loop.this_task:
                loop.close(task)
        self.timers.clear()
        self.tasks.clear()

        self.transition_out = self.layout.get_transition_out()

        # shut down anyone who is waiting for the result
        if _kill_taker:
            self.result_box.maybe_close()

        if CURRENT_LAYOUT is self:
            # fade to black -- backlight is off while no layout is running
            backlight_fade(BacklightLevels.NONE)

            set_current_layout(None)
            if __debug__:
                if self.button_request_ack_pending:
                    raise wire.FirmwareError("button request ack pending")
                self.notify_debuglink(None)

    async def get_result(self) -> T:
        """Wait for, and return, the result of this UI layout."""
        if self.is_ready():
            self.start()
        # else we are (a) still running or (b) already finished
        try:
            if self.context is not None and self.result_box.is_empty():
                self._start_task(self._handle_usb_iface())
            return await self.result_box
        finally:
            self.stop()

    def request_complete_repaint(self) -> None:
        """Request a complete repaint of the layout."""
        msg = self.layout.request_complete_repaint()
        assert msg is None

    def _event(self, event_call: Callable[..., LayoutState | None], *args: Any) -> None:
        """Process an event coming out of the Rust layout. Set is as a result and shut
        down the layout if appropriate, do nothing otherwise."""
        if __debug__ and CURRENT_LAYOUT is not self:
            raise wire.FirmwareError("layout received an event but it is not running")

        first_paint = False
        state = event_call(*args)
        self.transition_out = self.layout.get_transition_out()

        if state is LayoutState.DONE:
            self._emit_message(self.layout.return_value())

        elif state is LayoutState.ATTACHED:
            first_paint = True
            self.button_request_ack_pending = self._button_request()
            if self.button_request_ack_pending:
                state = LayoutState.TRANSITIONING
            elif __debug__:
                self.notify_debuglink(self)

        if state is not None:
            self.state = state

        if first_paint:
            self._first_paint()
        else:
            self._paint()

    def _button_request(self) -> bool:
        """Process a button request coming out of the Rust layout."""
        if __debug__ and not self.button_request_box.is_empty():
            raise wire.FirmwareError(
                "button request already pending -- "
                "don't forget to yield your input flow from time to time ^_^"
            )

        res = self.layout.button_request()
        if res is None:
            return False

        if self.context is None:
            return False

        # in production, we don't want this to fail, hence replace=True
        self.button_request_box.put(res, replace=True)
        return True

    def _paint(self) -> None:
        """Paint the layout and ensure that homescreen cache is properly invalidated."""
        import storage.cache as storage_cache

        painted = self.layout.paint()
        if painted:
            refresh()
        if storage_cache.homescreen_shown is not None and painted:
            storage_cache.homescreen_shown = None

    def _first_paint(self) -> None:
        """Paint the layout for the first time after starting it.

        This is a separate call in order for homescreens to be able to override and not
        paint when the screen contents are still valid.
        """
        # Clear the screen of any leftovers.
        self.request_complete_repaint()
        self._paint()

        # Turn the brightness on.
        backlight_fade(self.backlight_level)

    def _set_timer(self, token: int, duration_ms: int) -> None:
        """Timer callback for Rust layouts."""

        async def timer_task() -> None:
            self.timers.pop(token)
            try:
                self._event(self.layout.timer, token)
            except Shutdown:
                pass

        if token == _REQUEST_ANIMATION_FRAME and token in self.timers:
            # do not schedule another animation frame if one is already scheduled
            return

        task = self.timers.get(token)
        if task is None:
            task = timer_task()
            self.timers[token] = task

        deadline = utime.ticks_add(utime.ticks_ms(), duration_ms)
        loop.schedule(task, deadline=deadline, reschedule=True)

    def _emit_message(self, msg: Any) -> None:
        """Process a message coming out of the Rust layout. Set is as a result and shut
        down the layout if appropriate, do nothing otherwise."""
        # when emitting a message, there should not be another one already waiting
        assert self.result_box.is_empty()
        self.stop(_kill_taker=False)
        self.result_box.put(msg)
        raise SHUTDOWN

    def create_tasks(self) -> Iterator[loop.Task]:
        """Set up background tasks for a layout.

        Called from `start()`. Creates and yields a list of background tasks, typically
        event handlers for different interfaces.

        Override and then `yield from super().create_tasks()` to add more tasks."""
        if utils.USE_BUTTON:
            yield self._handle_input_iface(io.BUTTON, self.layout.button_event)
        if utils.USE_TOUCH:
            yield self._handle_input_iface(io.TOUCH, self.layout.touch_event)

    def _handle_input_iface(
        self, iface: int, event_call: Callable[..., LayoutState | None]
    ) -> Generator:
        """Task that is waiting for the user input."""
        touch = loop.wait(iface)
        try:
            while True:
                # Using `yield` instead of `await` to avoid allocations.
                event = yield touch
                workflow.idle_timer.touch()
                self._event(event_call, *event)
        except Shutdown:
            return
        finally:
            touch.close()

    async def _handle_usb_iface(self) -> None:
        if self.context is None:
            return
        while True:
            try:
                br_code, br_name = await loop.race(
                    self.context.read(()),
                    self.button_request_box,
                )

                if __debug__:
                    log.info(__name__, "ButtonRequest sent: %s", br_name)
                await self.context.call(
                    ButtonRequest(
                        code=br_code, pages=self.layout.page_count(), name=br_name
                    ),
                    ButtonAck,
                )
                if __debug__:
                    log.info(__name__, "ButtonRequest acked: %s", br_name)

                if (
                    self.button_request_ack_pending
                    and self.state is LayoutState.TRANSITIONING
                ):
                    self.button_request_ack_pending = False
                    self.state = LayoutState.ATTACHED
                    if __debug__:
                        self.notify_debuglink(self)
            except Exception:
                raise

    def _task_finalizer(self, task: loop.Task, value: Any) -> None:
        if value is None:
            # all is good
            if __debug__:
                log.debug(__name__, "UI task exited by itself: %s", task)
            return

        if isinstance(value, GeneratorExit):
            if __debug__:
                log.debug(__name__, "UI task was stopped: %s", task)
            return

        if isinstance(value, BaseException):
            if __debug__ and value.__class__.__name__ != "UnexpectedMessage":
                log.error(
                    __name__, "UI task died: %s (%s)", task, value.__class__.__name__
                )
            try:
                self._emit_message(value)
            except Shutdown:
                pass

        if __debug__:
            log.error(__name__, "UI task returned non-None: %s (%s)", task, value)

    def _start_task(self, task: loop.Task) -> None:
        self.tasks.add(task)
        loop.schedule(task, finalizer=self._task_finalizer)

    def __del__(self) -> None:
        self.layout.__del__()


class ProgressLayout:
    """Progress layout.

    Simplified version of the general Layout object, for the purpose of showing spinners
    and loaders that are shown "in the background" of a running workflow. Does not run
    background tasks, does not respond to timers.

    Participates in global layout management. This is to track whether the progress bar
    is currently displayed, who needs to redraw and when.
    """

    def __init__(self, layout: LayoutObj[UiResult]) -> None:
        self.layout = layout
        self.transition_out = None

    def is_layout_attached(self) -> bool:
        return True

    def report(self, value: int, description: str | None = None) -> None:
        """Report a progress step.

        Starts the layout if it is not running.

        `value` can be in range from 0 to 1000.
        """
        if CURRENT_LAYOUT is not self:
            self.start()

        if utils.DISABLE_ANIMATION:
            return

        msg = self.layout.progress_event(value, description or "")
        assert msg is None
        if self.layout.paint():
            refresh()

    def start(self) -> None:
        global CURRENT_LAYOUT

        if CURRENT_LAYOUT is not self and CURRENT_LAYOUT is not None:
            CURRENT_LAYOUT.stop()

        assert CURRENT_LAYOUT is None
        set_current_layout(self)

        self.layout.request_complete_repaint()
        painted = self.layout.paint()
        backlight_fade(BacklightLevels.NORMAL)
        if painted:
            refresh()

    def stop(self) -> None:
        global CURRENT_LAYOUT

        if CURRENT_LAYOUT is self:
            set_current_layout(None)
