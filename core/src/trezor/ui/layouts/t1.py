from trezor import log, ui, wire
from trezor.enums import ButtonRequestType

from trezorui2 import layout_new_confirm_action

from .common import interact

if False:
    from typing import NoReturn, Type, Union

    ExceptionType = Union[BaseException, Type[BaseException]]


async def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str | bytes | None = "OK",
    verb_cancel: str | bytes | None = "cancel",
    hold: bool = False,
    hold_danger: bool = False,
    icon: str | None = None,
    icon_color: int | None = None,
    reverse: bool = False,
    larger_vspace: bool = False,
    exc: ExceptionType = wire.ActionCancelled,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    if isinstance(verb, bytes) or isinstance(verb_cancel, bytes):
        raise NotImplementedError

    if description is not None and description_param is not None:
        if description_param_font != ui.BOLD:
            log.error(__name__, "confirm_action description_param_font not implemented")
        description = description.format(description_param)

    if hold:
        log.error(__name__, "confirm_action hold not implemented")

    result = await interact(
        ctx,
        ui.RustLayout(
            layout_new_confirm_action(
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
    if result == 1:
        raise exc


async def show_error_and_raise(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "Error",
    subheader: str | None = None,
    button: str = "Close",
    red: bool = False,
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
