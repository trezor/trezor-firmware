import utime
import utimeq
from typing import TYPE_CHECKING

from trezor import log, ui, utils, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

try:
    UI2 = True
    import trezorui2  # noqa: F401
except ImportError:
    UI2 = False


if TYPE_CHECKING:
    from typing import Any, Awaitable

    LayoutType = Awaitable[Any]
    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]


async def button_request(
    ctx: wire.GenericContext,
    br_type: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int | None = None,
) -> None:
    if __debug__:
        log.debug(__name__, "ButtonRequest.type=%s", br_type)
    workflow.close_others()
    if pages is not None:
        await ctx.call(ButtonRequest(code=code, pages=pages), ButtonAck)
    else:
        await ctx.call(ButtonRequest(code=code), ButtonAck)


async def interact(
    layout: LayoutType,
    br_type: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> Any:
    ctx = wire.get_context()
    try:
        previous_layout = ui.RUNNING_LAYOUT
        if previous_layout is not None:
            await previous_layout.do_cancel()

        while ui.RUNNING_LAYOUT is not None:
            yield
        assert ui.RUNNING_LAYOUT is None
        ui.RUNNING_LAYOUT = layout

        if layout.__class__.__name__ == "Paginated":
            from ..components.tt.scroll import Paginated

            assert isinstance(layout, Paginated)
            return await layout.interact(ctx, code=br_code)
        elif hasattr(layout, "page_count") and layout.page_count() > 1:  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
            if br_type is not None:
                await button_request(ctx, br_type, br_code, pages=layout.page_count())  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
            return await ctx.wait(layout)
        else:
            if br_type is not None:
                await button_request(ctx, br_type, br_code)
            return await ctx.wait(layout)

    finally:
        ui.RUNNING_LAYOUT = None


if UI2:

    from trezor import io, loop

    class RustLayout(ui.Layout):
        def __init__(self, layout: Any):
            super().__init__()
            self.layout = layout
            self.timers = utimeq.utimeq(64)
            self.timer_task: loop.Task | None = None

        def set_timer(self, token: int, duration: int) -> None:
            deadline = utime.ticks_add(utime.ticks_ms(), duration)
            self.timers.push(deadline, token, token)
            if self.timer_task:
                min_deadline = self.timers.peektime()
                loop.schedule(
                    self.timer_task, min_deadline, min_deadline, reschedule=True
                )

        if __debug__:

            def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
                from apps.debug import confirm_signal, input_signal

                return (
                    self.handle_timers(),
                    self.handle_input_and_rendering(),
                    confirm_signal(),
                    input_signal(),
                )

            def read_content(self) -> list[str]:
                result = []

                def callback(*args):
                    for arg in args:
                        result.append(str(arg))

                self.layout.trace(callback)
                result = " ".join(result).split("\n")
                return result

        else:

            def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
                return self.handle_timers(), self.handle_input_and_rendering()

        def handle_timers(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
            entry = [0, 0, 0]
            while True:
                delay = 1000
                if self.timers:
                    delay = self.timers.peektime() - utime.ticks_ms()
                yield loop.sleep(max(0, delay))

                now = utime.ticks_ms()
                while self.timers and self.timers.peektime() <= now:
                    self.timers.pop(entry)
                    msg = self.layout.timer(entry[1])
                    self.layout.paint()
                    if msg is not None:
                        raise ui.Result(msg)

        if utils.MODEL in ("T",):

            def _before_render(self) -> None:
                # Clear the screen of any leftovers.
                ui.backlight_fade(ui.style.BACKLIGHT_DIM)
                ui.display.clear()

                if __debug__ and self.should_notify_layout_change:
                    from apps.debug import notify_layout_change

                    # notify about change and do not notify again until next await.
                    # (handle_rendering might be called multiple times in a single await,
                    # because of the endless loop in __iter__)
                    self.should_notify_layout_change = False
                    notify_layout_change(self)

                # Turn the brightness on again.
                ui.backlight_fade(self.BACKLIGHT_LEVEL)

            def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
                touch = loop.wait(io.TOUCH)
                self._before_render()
                self.layout.attach_timer_fn(self.set_timer)
                self.layout.paint()
                # self.layout.bounds()
                while True:
                    # Using `yield` instead of `await` to avoid allocations.
                    event, x, y = yield touch
                    workflow.idle_timer.touch()
                    msg = None
                    if event in (io.TOUCH_START, io.TOUCH_MOVE, io.TOUCH_END):
                        msg = self.layout.touch_event(event, x, y)
                    self.layout.paint()
                    # self.layout.bounds()
                    if msg is not None:
                        raise ui.Result(msg)

        elif utils.MODEL in ("1", "R"):

            def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
                button = loop.wait(io.BUTTON)
                ui.display.clear()
                self.layout.attach_timer_fn(self.set_timer)
                self.layout.paint()

                if __debug__ and self.should_notify_layout_change:
                    from apps.debug import notify_layout_change

                    self.should_notify_layout_change = False
                    notify_layout_change(self)

                while True:
                    # Using `yield` instead of `await` to avoid allocations.
                    event, button_num = yield button
                    workflow.idle_timer.touch()
                    msg = None
                    if event in (io.BUTTON_PRESSED, io.BUTTON_RELEASED):
                        msg = self.layout.button_event(event, button_num)
                    self.layout.paint()
                    if msg is not None:
                        raise ui.Result(msg)
