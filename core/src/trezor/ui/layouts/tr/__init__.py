from typing import TYPE_CHECKING, Sequence

from trezor import io, log, loop, ui, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.utils import DISABLE_ANIMATION

import trezorui2

from ..common import button_request, interact

if TYPE_CHECKING:
    from typing import Any, NoReturn, Type

    ExceptionType = BaseException | Type[BaseException]


if __debug__:
    trezorui2.disable_animation(bool(DISABLE_ANIMATION))


def is_confirmed(x: Any) -> bool:
    return x is trezorui2.CONFIRMED


class RustLayout(ui.Layout):
    # pylint: disable=super-init-not-called
    def __init__(self, layout: Any):
        self.layout = layout
        self.timer = loop.Timer()
        self.layout.set_timer_fn(self.set_timer)

    def set_timer(self, token: int, deadline: int) -> None:
        self.timer.schedule(deadline, token)

    def create_tasks(self) -> tuple[loop.Task, ...]:
        return self.handle_input_and_rendering(), self.handle_timers()

    def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        button = loop.wait(io.BUTTON)
        ui.display.clear()
        self.layout.paint()
        ui.refresh()
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            event, button_num = yield button
            workflow.idle_timer.touch()
            msg = None
            if event in (io.BUTTON_PRESSED, io.BUTTON_RELEASED):
                msg = self.layout.button_event(event, button_num)
            if msg is not None:
                raise ui.Result(msg)
            self.layout.paint()
            ui.refresh()

    def handle_timers(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            token = yield self.timer
            msg = self.layout.timer(token)
            if msg is not None:
                raise ui.Result(msg)
            self.layout.paint()
            ui.refresh()


async def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str = "CONFIRM",
    verb_cancel: str | None = None,
    hold: bool = False,
    reverse: bool = False,
    exc: ExceptionType = wire.ActionCancelled,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    if verb_cancel is not None:
        verb_cancel = verb_cancel.upper()

    if description is not None and description_param is not None:
        if description_param_font != ui.BOLD:
            log.error(__name__, "confirm_action description_param_font not implemented")
        description = description.format(description_param)

    if hold:
        log.error(__name__, "confirm_action hold not implemented")

    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_action(
                title=title.upper(),
                action=action,
                description=description,
                verb=verb,
                verb_cancel=verb_cancel,
                hold=hold,
                reverse=reverse,
            )
        ),
        br_type,
        br_code,
    )
    if not is_confirmed(result):
        raise exc


async def confirm_text(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title=title.upper(),
                data=data,
                description=description,
            )
        ),
        br_type,
        br_code,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def show_success(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title="Success",
                data=content,
                description="",
            )
        ),
        br_type,
        br_code=ButtonRequestType.Other,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    *,
    case_sensitive: bool = True,
    address_qr: str | None = None,
    title: str = "Confirm address",
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    address_extra: str | None = None,
    title_qr: str | None = None,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title="ADDRESS",
                data=address,
                description="Confirm address",
            )
        ),
        "show_address",
        ButtonRequestType.Address,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def confirm_output(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
    title: str = "Confirm sending",
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title=title,
                data=f"Send {amount} to {address}?",
                description="Confirm Output",
            )
        ),
        "confirm_output",
        br_code,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def confirm_total(
    ctx: wire.GenericContext,
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    title: str = "Confirm transaction",
    total_label: str = "Total amount:\n",
    fee_label: str = "\nincluding fee:\n",
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title=title,
                data=f"{total_label}{total_amount}\n{fee_label}{fee_amount}",
                description="Confirm Output",
            )
        ),
        br_type,
        br_code,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def confirm_blob(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    ask_pagination: bool = False,
) -> None:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_text(
                title=title,
                data=str(data),
                description=description,
            )
        ),
        br_type,
        br_code,
    )
    if not is_confirmed(result):
        raise wire.ActionCancelled


async def request_pin_on_device(
    ctx: wire.GenericContext,
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
) -> str:
    await button_request(ctx, "pin_device", code=ButtonRequestType.PinEntry)

    # TODO: this should not be callable on TR
    return "1234"


async def show_error_and_raise(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Close",
    exc: ExceptionType = wire.ActionCancelled,
) -> NoReturn:
    raise NotImplementedError


async def show_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    timeout_ms: int = 3000,
) -> None:
    raise NotImplementedError
