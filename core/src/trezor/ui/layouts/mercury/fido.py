from typing import TYPE_CHECKING

import trezorui2
from trezor.enums import ButtonRequestType

from ..common import interact
from . import RustLayout

if TYPE_CHECKING:
    from trezor.loop import AwaitableTask

if __debug__:
    from trezor import io, ui

    from ... import Result

    # needed solely for test_emu_u2f
    class _RustFidoLayoutImpl(RustLayout):
        def create_tasks(self) -> tuple[AwaitableTask, ...]:
            return (
                self.handle_input_and_rendering(),
                self.handle_timers(),
                self.handle_swipe(),
                self.handle_click_signal(),
                self.handle_debug_confirm(),
            )

        async def handle_debug_confirm(self) -> None:
            from apps.debug import result_signal

            _event_id, result = await result_signal()
            if result is not trezorui2.CONFIRMED:
                raise Result(result)

            for event, x, y in (
                (io.TOUCH_START, 120, 160),
                (io.TOUCH_MOVE, 120, 130),
                (io.TOUCH_END, 120, 100),
                (io.TOUCH_START, 120, 120),
                (io.TOUCH_END, 120, 120),
            ):
                msg = self.layout.touch_event(event, x, y)
                if self.layout.paint():
                    ui.refresh()
                if msg is not None:
                    raise Result(msg)

    _RustFidoLayout = _RustFidoLayoutImpl

else:
    _RustFidoLayout = RustLayout


async def confirm_fido(
    header: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> int:
    """Webauthn confirmation for one or more credentials."""
    confirm = _RustFidoLayout(
        trezorui2.confirm_fido(
            title=header,
            app_name=app_name,
            icon_name=icon_name,
            accounts=accounts,
        )
    )
    result = await interact(confirm, "confirm_fido", ButtonRequestType.Other)

    # The Rust side returns either an int or `CANCELLED`. We detect the int situation
    # and assume cancellation otherwise.
    if isinstance(result, tuple):
        return result[1]

    # Late import won't get executed on the happy path.
    from trezor.wire import ActionCancelled

    raise ActionCancelled


async def confirm_fido_reset() -> bool:
    from trezor import TR

    confirm = RustLayout(
        trezorui2.confirm_action(
            title=TR.fido__title_reset,
            action=TR.fido__erase_credentials,
            description=TR.words__really_wanna,
            reverse=True,
            prompt_screen=True,
        )
    )
    return (await confirm) is trezorui2.CONFIRMED
