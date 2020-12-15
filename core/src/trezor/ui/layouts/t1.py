from ubinascii import hexlify

from trezor import log, ui, wire
from trezor.enums import ButtonRequestType

from trezorui2 import (
    layout_new_confirm_action,
    layout_new_confirm_blob,
    layout_new_confirm_coinjoin,
    layout_new_confirm_metadata,
    layout_new_confirm_modify_fee,
    layout_new_confirm_output,
    layout_new_confirm_reset,
    layout_new_confirm_total,
    layout_new_path_warning,
    layout_new_show_address,
    layout_new_show_modal,
)

from ..components.common.confirm import is_confirmed, raise_if_cancelled
from ..components.common.homescreen import HomescreenBase
from ..components.t1.homescreen import Homescreen
from ..constants.t1 import MONO_ADDR_PER_LINE
from .common import interact

if False:
    from typing import Awaitable, Iterable, Sequence, NoReturn, Type, Union

    ExceptionType = Union[BaseException, Type[BaseException]]


async def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str | bytes | None = "CONFIRM",
    verb_cancel: str | bytes | None = "CANCEL",
    hold: bool = False,
    hold_danger: bool = False,
    icon: str | None = None,  # TODO cleanup @ redesign
    icon_color: int | None = None,  # TODO cleanup @ redesign
    reverse: bool = False,  # TODO cleanup @ redesign
    larger_vspace: bool = False,  # TODO cleanup @ redesign
    exc: ExceptionType = wire.ActionCancelled,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    # TODO: description_param_font
    # TODO: hold
    if isinstance(verb, bytes) or isinstance(verb_cancel, bytes):
        raise NotImplementedError

    if description is not None and description_param is not None:
        if description_param_font != ui.BOLD:
            log.error(__name__, "confirm_action description_param_font not implemented")
        description = description.format(description_param)

    if hold:
        verb = "HOLD TO CONFIRM"
        verb_cancel = "X"

    if action is not None:
        # remove custom linebreaks for TT
        action = action.replace("\n", " ")

    if description is not None:
        description = description.replace("\n", " ")

    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_action(
                    title=None,  # title=title.upper(),
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
        ),
        exc,
    )


async def confirm_reset_device(
    ctx: wire.GenericContext, prompt: str, recovery: bool = False
) -> None:
    # XXX recovery ignored because theres no titlebar, info should be in prompt
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(layout_new_confirm_reset(prompt=prompt.replace("\n", " "))),
            "recover_device" if recovery else "setup_device",
            ButtonRequestType.ProtectCall
            if recovery
            else ButtonRequestType.ResetDevice,
        )
    )


async def confirm_backup(ctx: wire.GenericContext) -> bool:
    if is_confirmed(
        await interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_action(
                    title=None,
                    action="New wallet created successfully!",
                    description="You should back up your new wallet right now.",
                    verb="BACK UP",
                    verb_cancel="SKIP",
                    hold=False,
                    reverse=False,
                )
            ),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    ):
        return True

    confirmed = is_confirmed(
        await interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_action(
                    title="SKIP THE BACKUP?",
                    action=None,
                    description="You can back up your Trezor once, at any time.",
                    verb="BACK UP",
                    verb_cancel="SKIP",
                    hold=False,
                    reverse=False,
                )
            ),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    )
    return confirmed


async def confirm_path_warning(
    ctx: wire.GenericContext, path: str, path_type: str = "ADDRESS PATH"
) -> None:
    # text.mono(*break_path_to_lines(path, MONO_CHARS_PER_LINE))
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_path_warning(path=path, title="WRONG {path_type.upper()}")
            ),
            "path_warning",
            ButtonRequestType.UnknownDerivationPath,
        )
    )


def _show_qr(
    address: str,
) -> ui.Layout:
    # QR_COEF = 2 if len(address) < QR_SIZE_THRESHOLD else 1
    # qr = Qr(address, QR_X, QR_Y, QR_COEF)
    # return Confirm(qr, confirm="CONTINUE", cancel="")
    raise NotImplementedError


# TODO: pagination
def _show_address(
    address: str,
    title: str,
    network: str | None = None,
    extra: str | None = None,
) -> ui.Layout:
    #    text.mono(*_split_address(address))
    return ui.RustLayout(
        layout_new_show_address(
            title=title.upper(), address=address, network=network, extra=extra
        )
    )


# TODO: Rust Confirm
def _show_xpub(xpub: str, title: str, cancel: str) -> ui.Layout:
    return ui.RustLayout(
        layout_new_confirm_blob(
            title=title.upper(), description="xpub not implemented", data=xpub
        )
    )


async def show_xpub(
    ctx: wire.GenericContext, xpub: str, title: str, cancel: str
) -> None:
    await raise_if_cancelled(
        interact(
            ctx,
            _show_xpub(xpub, title, cancel),
            "show_xpub",
            ButtonRequestType.PublicKey,
        )
    )


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    address_qr: str | None = None,
    title: str = "Confirm address",
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    address_extra: str | None = None,
    title_qr: str | None = None,  # ignored, no room for title
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        if is_confirmed(
            await interact(
                ctx,
                _show_address(address, title, network, extra=address_extra),
                "show_address",
                ButtonRequestType.Address,
            )
        ):
            break
        if is_confirmed(
            await interact(
                ctx,
                _show_qr(
                    address if address_qr is None else address_qr,
                ),
                "show_qr",
                ButtonRequestType.Address,
            )
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "NEXT" if i < len(xpubs) - 1 else "ADDRESS"
                title_xpub = f"XPUB #{i + 1}"
                title_xpub += " (yours)" if i == multisig_index else " (cosigner)"
                if is_confirmed(
                    await interact(
                        ctx,
                        _show_xpub(xpub, title=title_xpub, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                ):
                    return


def show_pubkey(
    ctx: wire.Context, pubkey: str, title: str = "Confirm public key"
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        br_type="show_pubkey",
        title=title,
        data=pubkey,
        br_code=ButtonRequestType.PublicKey,
        icon=ui.ICON_RECEIVE,
    )


async def _show_modal(
    ctx: wire.GenericContext,
    br_type: str,
    br_code: ButtonRequestType,
    title: str | None,
    subtitle: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    exc: ExceptionType = wire.ActionCancelled,
) -> None:
    if title is not None:
        title = title.upper()
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_show_modal(
                    title=title,
                    subtitle=subtitle,
                    content=content,
                    button_confirm=button_confirm,
                    button_cancel=button_cancel,
                )
            ),
            br_type,
            br_code,
        ),
        exc,
    )


async def show_error_and_raise(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "FAIL!",
    subheader: str | None = None,
    button: str = "CLOSE",
    red: bool = False,
    exc: ExceptionType = wire.ActionCancelled,
) -> NoReturn:
    await _show_modal(
        ctx,
        br_type=br_type,
        br_code=ButtonRequestType.Other,
        title=header,
        subtitle=subheader,
        content=content,
        button_confirm=None,
        button_cancel=button,
        exc=exc,
    )
    raise exc


def show_warning(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "WARNING!",
    subheader: str | None = None,
    button: str = "TRY AGAIN",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
    icon: str = ui.ICON_WRONG,
    icon_color: int = ui.RED,
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=br_code,
        title=header,
        subtitle=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
    )


def show_success(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "CLOSE",
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=ButtonRequestType.Success,
        title="SUCCESS!",
        subtitle=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
    )


async def confirm_output(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
    font_amount: int = ui.NORMAL,  # TODO cleanup @ redesign
    title: str = "TRANSACTION",
    subtitle: str | None = None,  # TODO cleanup @ redesign
    color_to: int = ui.FG,  # TODO cleanup @ redesign
    to_str: str = " to\n",  # TODO cleanup @ redesign
    to_paginated: bool = False,  # TODO cleanup @ redesign
    width: int = MONO_ADDR_PER_LINE,
    width_paginated: int = MONO_ADDR_PER_LINE - 1,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    # TODO: pagination
    # text.mono(*_split_address(address))
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_output(
                    address=address, amount=amount, title=title, subtitle=subtitle
                )
            ),
            "confirm_output",
            br_code,
        )
    )


async def should_show_more(
    ctx: wire.GenericContext,
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str = "Show all",
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
) -> bool:
    raise NotImplementedError


async def confirm_blob(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    ask_pagination: bool = False,
) -> None:
    # TODO: line breaking
    # TODO: pagination
    # TODO: ask_pagination
    # TODO: hold
    if isinstance(data, (bytes, bytearray)):
        data_str = hexlify(data).decode()
    else:
        data_str = data
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_blob(
                    title=title.upper(), description=description, data=data_str
                )
            ),
            br_type,
            br_code,
        )
    )


def confirm_address(
    ctx: wire.GenericContext,
    title: str,
    address: str,
    description: str | None = "Address:",
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        br_type=br_type,
        title=title,
        data=address,
        description=description,
        br_code=br_code,
    )


async def confirm_total(
    ctx: wire.GenericContext, total_amount: str, fee_amount: str
) -> None:
    # FIXME hold
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_total(
                    title="TRANSACTION",
                    label1="Total amount:",
                    amount1=total_amount,
                    label2="Fee included:",
                    amount2=fee_amount,
                )
            ),
            "confirm_total",
            ButtonRequestType.SignTx,
        )
    )


async def confirm_joint_total(
    ctx: wire.GenericContext, spending_amount: str, total_amount: str
) -> None:
    # FIXME hold
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_total(
                    title="JOINT TRANSACTION",
                    label1="You are contributing:",
                    amount1=spending_amount,
                    label2="to the total amount:",
                    amount2=total_amount,
                )
            ),
            "confirm_joint_total",
            ButtonRequestType.SignTx,
        )
    )


async def confirm_metadata(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hide_continue: bool = False,
    hold: bool = False,
    param_font: int = ui.BOLD,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    larger_vspace: bool = False,  # TODO cleanup @ redesign
) -> None:
    # FIXME: hold
    # FIXME: param_font
    if param:
        content = content.format(param)
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_metadata(
                    title=title.upper(),
                    content=content,
                    show_continue=not hide_continue,
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_replacement(
    ctx: wire.GenericContext, description: str, txid: str
) -> None:
    await confirm_blob(
        ctx,
        "confirm_replacement",
        title=description,
        data=txid,
        description="Confirm transaction ID:",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    ctx: wire.GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    raise NotImplementedError


async def confirm_modify_fee(
    ctx: wire.GenericContext,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> None:
    # TODO: hold
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_modify_fee(
                    title="MODIFY FEE",
                    sign=sign,
                    user_fee_change=user_fee_change,
                    total_fee_new=total_fee_new,
                )
            ),
            "modify_fee",
            ButtonRequestType.SignTx,
        )
    )


async def confirm_coinjoin(
    ctx: wire.GenericContext, fee_per_anonymity: str | None, total_fee: str
) -> None:
    # TODO: hold
    await raise_if_cancelled(
        interact(
            ctx,
            ui.RustLayout(
                layout_new_confirm_coinjoin(
                    title="AUTHORIZE COINJOIN",
                    fee_per_anonymity=fee_per_anonymity,
                    total_fee=total_fee,
                )
            ),
            "coinjoin_final",
            ButtonRequestType.Other,
        )
    )


async def confirm_sign_identity(
    ctx: wire.GenericContext, proto: str, identity: str, challenge_visual: str | None
) -> None:
    await confirm_blob(
        ctx,
        br_type="sign_identity",
        title=f"Sign {proto}".upper(),
        description=challenge_visual,
        data=identity,
        br_code=ButtonRequestType.Other,
    )


async def confirm_signverify(
    ctx: wire.GenericContext, coin: str, message: str, address: str | None = None
) -> None:
    if address:
        title = f"Verify {coin} message"
        br_type = "verify_message"
        # TODO breaking address

        await confirm_address(
            ctx,
            title=title.upper(),
            description="Confirm address:",
            address=address,
            br_type=br_type,
        )
    else:
        title = f"Sign {coin} message"
        br_type = "sign_message"

    await confirm_blob(
        ctx,
        br_type=br_type,
        title=title.upper(),
        data=message,
        br_code=ButtonRequestType.Other,
    )


async def show_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    timeout_ms: int = 3000,
) -> None:
    raise NotImplementedError


def draw_simple_text(title: str, description: str = "") -> None:
    ui.display.text_center(ui.WIDTH // 2, 32, title, ui.BOLD, ui.FG, ui.BG)
    ui.display.text_center(ui.WIDTH // 2, 48, description, ui.NORMAL, ui.FG, ui.BG)


def homescreen() -> HomescreenBase:
    return Homescreen()
