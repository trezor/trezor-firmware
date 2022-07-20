from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import log, ui, wire
from trezor.enums import ButtonRequestType

import trezorui2

from ...components.tt.button import ButtonContent
from ...components.tt.confirm import Confirm
from ...constants.tt import MONO_ADDR_PER_LINE
from ..common import RustLayout, interact

if TYPE_CHECKING:
    from typing import Any, Awaitable, Iterable, NoReturn, Sequence

    from ..common import PropertyType, ExceptionType


async def confirm_action(
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str | bytes | None = "CONFIRM",
    verb_cancel: str | bytes | None = None,
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
    if isinstance(verb, str):
        verb = verb.upper()
    if isinstance(verb_cancel, str):
        verb_cancel = verb_cancel.upper()

    if description is not None and description_param is not None:
        if description_param_font != ui.BOLD:
            log.error(__name__, "confirm_action description_param_font not implemented")
        description = description.format(description_param)

    result = await interact(
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
    if result is not trezorui2.CONFIRMED:
        raise exc


async def confirm_reset_device(prompt: str, recovery: bool = False) -> None:
    return await confirm_action(
        "recover_device" if recovery else "setup_device",
        "not implemented",
        action="not implemented",
    )


# TODO cleanup @ redesign
async def confirm_backup() -> bool:
    raise NotImplementedError


async def confirm_path_warning(path: str, path_type: str = "Path") -> None:
    result = await interact(
        RustLayout(
            trezorui2.show_warning(
                title="Unknown path",
                description=path,
            )
        ),
        "path_warning",
        ButtonRequestType.UnknownDerivationPath,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


def _show_xpub(xpub: str, title: str, cancel: str) -> ui.Layout:
    content = RustLayout(
        trezorui2.confirm_blob(
            title=title,
            data=xpub,
            verb_cancel=cancel,
        )
    )
    return content


async def show_xpub(xpub: str, title: str, cancel: str) -> None:
    result = await interact(
        _show_xpub(xpub, title, cancel),
        "show_xpub",
        ButtonRequestType.PublicKey,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def show_address(
    address: str,
    *,
    address_qr: str | None = None,
    case_sensitive: bool = True,
    title: str = "Confirm address",
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    address_extra: str | None = None,
    title_qr: str | None = None,
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        result = await interact(
            RustLayout(
                trezorui2.confirm_blob(
                    title=title.upper(),
                    data=address,
                    description=network or "",
                    extra=address_extra or "",
                    verb_cancel="QR",
                )
            ),
            "show_address",
            ButtonRequestType.Address,
        )
        if result is trezorui2.CONFIRMED:
            break

        result = await interact(
            RustLayout(
                trezorui2.show_qr(
                    address=address if address_qr is None else address_qr,
                    case_sensitive=case_sensitive,
                    title=title.upper() if title_qr is None else title_qr.upper(),
                    verb_cancel="XPUBs" if is_multisig else "ADDRESS",
                )
            ),
            "show_qr",
            ButtonRequestType.Address,
        )
        if result is trezorui2.CONFIRMED:
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "NEXT" if i < len(xpubs) - 1 else "ADDRESS"
                title_xpub = f"XPUB #{i + 1}"
                title_xpub += " (yours)" if i == multisig_index else " (cosigner)"
                result = await interact(
                    _show_xpub(xpub, title=title_xpub, cancel=cancel),
                    "show_xpub",
                    ButtonRequestType.PublicKey,
                )
                if result is trezorui2.CONFIRMED:
                    return


def show_pubkey(pubkey: str, title: str = "Confirm public key") -> Awaitable[None]:
    return confirm_blob(
        br_type="show_pubkey",
        title="Confirm public key",
        data=pubkey,
        br_code=ButtonRequestType.PublicKey,
        icon=ui.ICON_RECEIVE,
    )


async def _show_modal(
    br_type: str,
    br_code: ButtonRequestType,
    header: str,
    subheader: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    icon: str,
    icon_color: int,
    exc: ExceptionType = wire.ActionCancelled,
) -> None:
    raise NotImplementedError


async def show_error_and_raise(
    br_type: str,
    content: str,
    header: str = "Error",
    subheader: str | None = None,
    button: str = "Close",
    red: bool = False,
    exc: ExceptionType = wire.ActionCancelled,
) -> NoReturn:
    await _show_modal(
        br_type=br_type,
        br_code=ButtonRequestType.Other,
        header=header,
        subheader=subheader,
        content=content,
        button_confirm=None,
        button_cancel=button,
        icon=ui.ICON_WRONG,
        icon_color=ui.RED if red else ui.ORANGE_ICON,
        exc=exc,
    )
    raise exc


def show_warning(
    br_type: str,
    content: str,
    header: str = "Warning",
    subheader: str | None = None,
    button: str = "Try again",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
    icon: str = ui.ICON_WRONG,
    icon_color: int = ui.RED,
) -> Awaitable[None]:
    return _show_modal(
        br_type=br_type,
        br_code=br_code,
        header=header,
        subheader=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
        icon=icon,
        icon_color=icon_color,
    )


async def show_success(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Continue",
) -> None:
    result = await interact(
        RustLayout(
            trezorui2.show_success(
                title=content,
                description=subheader or "",
                button=button.upper(),
            )
        ),
        br_type,
        ButtonRequestType.Success,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_output(
    address: str,
    amount: str,
    font_amount: int = ui.NORMAL,  # TODO cleanup @ redesign
    title: str = "SENDING",
    subtitle: str | None = None,  # TODO cleanup @ redesign
    color_to: int = ui.FG,  # TODO cleanup @ redesign
    to_str: str = " to\n",  # TODO cleanup @ redesign
    to_paginated: bool = False,  # TODO cleanup @ redesign
    width: int = MONO_ADDR_PER_LINE,
    width_paginated: int = MONO_ADDR_PER_LINE - 1,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    icon: str = ui.ICON_SEND,
) -> None:
    title = title.upper()
    if title.startswith("CONFIRM "):
        title = title[len("CONFIRM ") :]

    result = await interact(
        RustLayout(
            trezorui2.confirm_output(
                title=title,
                description="To:",
                value=address,
            )
        ),
        "confirm_output",
        br_code,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled

    result = await interact(
        RustLayout(
            trezorui2.confirm_output(
                title=title,
                description="Amount:",
                value=amount,
            )
        ),
        "confirm_output",
        br_code,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_payment_request(
    recipient_name: str,
    amount: str,
    memos: list[str],
) -> Any:
    from ...components.common import confirm

    result = await interact(
        RustLayout(
            trezorui2.confirm_payment_request(
                description=f"{amount} to\n{recipient_name}",
                memos=memos,
            )
        ),
        "confirm_payment_request",
        ButtonRequestType.ConfirmOutput,
    )
    if result is trezorui2.CONFIRMED:
        return confirm.CONFIRMED
    elif result is trezorui2.INFO:
        return confirm.INFO
    else:
        raise wire.ActionCancelled


async def should_show_more(
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str = "Show all",
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
    confirm: ButtonContent = Confirm.DEFAULT_CONFIRM,
    major_confirm: bool = False,
) -> bool:
    raise NotImplementedError


async def confirm_blob(
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
    if isinstance(data, bytes):
        data = hexlify(data).decode()

    result = await interact(
        RustLayout(
            trezorui2.confirm_blob(
                title=title.upper(),
                description=description or "",
                data=data,
                ask_pagination=ask_pagination,
                hold=hold,
            )
        ),
        br_type,
        br_code,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


def confirm_address(
    title: str,
    address: str,
    description: str | None = "Address:",
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> Awaitable[None]:
    raise NotImplementedError


async def confirm_text(
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> None:
    raise NotImplementedError


def confirm_amount(
    title: str,
    amount: str,
    description: str = "Amount:",
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> Awaitable[None]:
    raise NotImplementedError


async def confirm_properties(
    br_type: str,
    title: str,
    props: Iterable[PropertyType],
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    raise NotImplementedError


async def confirm_total(
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    title: str = "SENDING",
    total_label: str = "Total amount:\n",
    fee_label: str = "\nincluding fee:\n",
    icon_color: int = ui.GREEN,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_output(
                title=title.upper(),
                description="Fee:",
                value=fee_amount,
            )
        ),
        "confirm_total",
        br_code,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled

    result = await interact(
        RustLayout(
            trezorui2.confirm_total(
                title=title.upper(),
                description="Total amount:",
                value=total_amount,
            )
        ),
        "confirm_total",
        br_code,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_joint_total(spending_amount: str, total_amount: str) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_joint_total(
                spending_amount=spending_amount,
                total_amount=total_amount,
            )
        ),
        "confirm_joint_total",
        ButtonRequestType.SignTx,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_metadata(
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
    if param:
        content = content.format(param)

    if br_type == "fee_over_threshold":
        layout = trezorui2.show_warning(
            title="Unusually high fee",
            description=param or "",
        )
    elif br_type == "change_count_over_threshold":
        layout = trezorui2.show_warning(
            title="A lot of change-outputs",
            description=f"{param} outputs" if param is not None else "",
        )
    else:
        if param is not None:
            content = content.format(param)
        # TODO: "unverified external inputs"

        layout = trezorui2.confirm_action(
            title=title.upper(),
            verb="NEXT",
            description=content,
            hold=hold,
        )

    result = await interact(
        RustLayout(layout),
        br_type,
        br_code,
    )

    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_replacement(description: str, txid: str) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_blob(
                title=description.upper(),
                description="Confirm transaction ID:",
                data=txid,
            )
        ),
        "confirm_replacement",
        ButtonRequestType.SignTx,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_modify_output(
                address=address,
                sign=sign,
                amount_change=amount_change,
                amount_new=amount_new,
            )
        ),
        "modify_output",
        ButtonRequestType.ConfirmOutput,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_modify_fee(
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_modify_fee(
                sign=sign,
                user_fee_change=user_fee_change,
                total_fee_new=total_fee_new,
            )
        ),
        "modify_fee",
        ButtonRequestType.SignTx,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def confirm_coinjoin(
    coin_name: str, max_rounds: int, max_fee_per_vbyte: str
) -> None:
    result = await interact(
        RustLayout(
            trezorui2.confirm_coinjoin(
                coin_name=coin_name,
                max_rounds=str(max_rounds),
                max_feerate=f"{max_fee_per_vbyte} sats/vbyte",
            )
        ),
        "coinjoin_final",
        ButtonRequestType.Other,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


# TODO cleanup @ redesign
async def confirm_sign_identity(
    proto: str, identity: str, challenge_visual: str | None
) -> None:
    raise NotImplementedError


async def confirm_signverify(
    coin: str, message: str, address: str, verify: bool
) -> None:
    if verify:
        title = f"VERIFY {coin} MESSAGE"
        br_type = "verify_message"
    else:
        title = f"SIGN {coin} MESSAGE"
        br_type = "sign_message"

    result = await interact(
        RustLayout(
            trezorui2.confirm_blob(
                title=title,
                description="Confirm address:",
                data=address,
            )
        ),
        br_type,
        ButtonRequestType.Other,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled

    result = await interact(
        RustLayout(
            trezorui2.confirm_blob(
                title=title,
                description="Confirm message:",
                data=message,
            )
        ),
        br_type,
        ButtonRequestType.Other,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def show_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    timeout_ms: int = 3000,
) -> None:
    raise NotImplementedError


def draw_simple_text(title: str, description: str = "") -> None:
    log.error(__name__, "draw_simple_text not implemented")


async def request_passphrase_on_device(max_len: int) -> str:
    keyboard = RustLayout(
        trezorui2.request_passphrase(prompt="Enter passphrase", max_len=max_len)
    )
    result = await interact(
        keyboard, "passphrase_device", ButtonRequestType.PassphraseEntry
    )
    if result is trezorui2.CANCELLED:
        raise wire.ActionCancelled("Passphrase entry cancelled")

    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
) -> str:
    warning = "Wrong PIN" if "Wrong" in prompt else None

    if attempts_remaining is None:
        subprompt = ""
    elif attempts_remaining == 1:
        prompt = "Enter PIN"
        subprompt = "Last attempt"
    else:
        prompt = "Enter PIN"
        subprompt = f"{attempts_remaining} tries left"

    dialog = RustLayout(
        trezorui2.request_pin(
            prompt=prompt,
            subprompt=subprompt,
            allow_cancel=allow_cancel,
            warning=warning,
        )
    )
    while True:
        result = await interact(dialog, "pin_device", ButtonRequestType.PinEntry)
        if result is trezorui2.CANCELLED:
            raise wire.PinCancelled
        assert isinstance(result, str)
        return result
