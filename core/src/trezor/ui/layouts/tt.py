from micropython import const

from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.ui.container import Container
from trezor.ui.loader import LoaderDanger
from trezor.ui.qr import Qr
from trezor.utils import chunks

from ..components.common import break_path_to_lines
from ..components.common.confirm import is_confirmed, raise_if_cancelled
from ..components.tt.button import ButtonCancel, ButtonDefault
from ..components.tt.confirm import Confirm, HoldToConfirm
from ..components.tt.scroll import Paginated, paginate_text
from ..components.tt.text import Span, Text
from ..constants.tt import (
    MONO_CHARS_PER_LINE,
    MONO_HEX_PER_LINE,
    QR_SIZE_THRESHOLD,
    QR_X,
    QR_Y,
    TEXT_MAX_LINES,
)
from .common import interact

if False:
    from typing import (
        Iterator,
        Sequence,
        Type,
        Union,
        Awaitable,
        NoReturn,
    )

    from ..components.common.text import TextContent

    ExceptionType = Union[BaseException, Type[BaseException]]

__all__ = (
    "confirm_action",
    "confirm_reset_device",
    "confirm_backup",
    "confirm_path_warning",
    "confirm_sign_identity",
    "confirm_signverify",
    "show_address",
    "show_error_and_raise",
    "show_pubkey",
    "show_success",
    "show_xpub",
    "show_warning",
    "confirm_output",
    "confirm_decred_sstx_submission",
    "confirm_hex",
    "confirm_total",
    "confirm_joint_total",
    "confirm_metadata",
    "confirm_replacement",
    "confirm_modify_output",
    "confirm_modify_fee",
    "confirm_coinjoin",
)


async def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str | bytes | None = Confirm.DEFAULT_CONFIRM,
    verb_cancel: str | bytes | None = Confirm.DEFAULT_CANCEL,
    hold: bool = False,
    hold_danger: bool = False,
    icon: str | None = None,  # TODO cleanup @ redesign
    icon_color: int | None = None,  # TODO cleanup @ redesign
    reverse: bool = False,  # TODO cleanup @ redesign
    larger_vspace: bool = False,  # TODO cleanup @ redesign
    exc: ExceptionType = wire.ActionCancelled,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    text = Text(
        title,
        icon if icon is not None else ui.ICON_DEFAULT,
        icon_color if icon_color is not None else ui.ORANGE_ICON,
        new_lines=False,
    )

    if reverse and description is not None:
        text.format_parametrized(
            description,
            description_param if description_param is not None else "",
            param_font=description_param_font,
        )
    elif action is not None:
        text.bold(action)

    if action is not None and description is not None:
        text.br()
        if larger_vspace:
            text.br_half()

    if reverse and action is not None:
        text.bold(action)
    elif description is not None:
        text.format_parametrized(
            description,
            description_param if description_param is not None else "",
            param_font=description_param_font,
        )

    cls = HoldToConfirm if hold else Confirm
    kwargs = {}
    if hold_danger:
        kwargs = {"loader_style": LoaderDanger, "confirm_style": ButtonCancel}
    await raise_if_cancelled(
        interact(
            ctx,
            cls(text, confirm=verb, cancel=verb_cancel, **kwargs),
            br_type,
            br_code,
        ),
        exc,
    )


async def confirm_reset_device(ctx: wire.GenericContext, prompt: str) -> None:
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    text.bold(prompt)
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to ")
    text.bold("https://trezor.io/tos")
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text, major_confirm=True),
            "setup_device",
            ButtonRequestType.ResetDevice,
        )
    )


# TODO cleanup @ redesign
async def confirm_backup(ctx: wire.GenericContext) -> bool:
    text1 = Text("Success", ui.ICON_CONFIRM, ui.GREEN)
    text1.bold("New wallet created", "successfully!")
    text1.br_half()
    text1.normal("You should back up your", "new wallet right now.")

    text2 = Text("Warning", ui.ICON_WRONG, ui.RED)
    text2.bold("Are you sure you want", "to skip the backup?")
    text2.br_half()
    text2.normal("You can back up your", "Trezor once, at any time.")

    if is_confirmed(
        await interact(
            ctx,
            Confirm(text1, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    ):
        return True

    confirmed = is_confirmed(
        await interact(
            ctx,
            Confirm(text2, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    )
    return confirmed


async def confirm_path_warning(ctx: wire.GenericContext, path: str) -> None:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*break_path_to_lines(path, MONO_CHARS_PER_LINE))
    text.normal("is unknown.", "Are you sure?")
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text),
            "path_warning",
            ButtonRequestType.UnknownDerivationPath,
        )
    )


def _show_qr(
    address: str,
    desc: str,
    cancel: str = "Address",
) -> Confirm:
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)

    return Confirm(Container(qr, text), cancel=cancel, cancel_style=ButtonDefault)


def _split_address(address: str) -> Iterator[str]:
    return chunks(address, MONO_CHARS_PER_LINE)


def _truncate_hex(
    hex_data: str,
    lines: int = TEXT_MAX_LINES,
    width: int = MONO_HEX_PER_LINE,
    middle: bool = False,
) -> Iterator[str]:
    if len(hex_data) >= width * lines:
        if middle:
            hex_data = (
                hex_data[: lines * width // 2 - 1]
                + "..."
                + hex_data[-lines * width // 2 + 2 :]
            )
        else:
            hex_data = hex_data[: (width * lines - 3)] + "..."
    return chunks(hex_data, width)


def _show_address(
    address: str,
    desc: str,
    network: str | None = None,
) -> Confirm:
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*_split_address(address))

    return Confirm(text, cancel="QR", cancel_style=ButtonDefault)


def _show_xpub(xpub: str, desc: str, cancel: str) -> Paginated:
    pages: list[ui.Component] = []
    for lines in chunks(list(chunks(xpub, 16)), 5):
        text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
        text.mono(*lines)
        pages.append(text)

    content = Paginated(pages)

    content.pages[-1] = Confirm(
        content.pages[-1],
        cancel=cancel,
        cancel_style=ButtonDefault,
    )

    return content


async def show_xpub(
    ctx: wire.GenericContext, xpub: str, desc: str, cancel: str
) -> None:
    await raise_if_cancelled(
        interact(
            ctx,
            _show_xpub(xpub, desc, cancel),
            "show_xpub",
            ButtonRequestType.PublicKey,
        )
    )


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    address_qr: str | None = None,
    desc: str = "Confirm address",
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = [],
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        if is_confirmed(
            await interact(
                ctx,
                _show_address(address, desc, network),
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
                    desc,
                    cancel="XPUBs" if is_multisig else "Address",
                ),
                "show_qr",
                ButtonRequestType.Address,
            )
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "Next" if i < len(xpubs) - 1 else "Address"
                desc_xpub = "XPUB #%d" % (i + 1)
                desc_xpub += " (yours)" if i == multisig_index else " (cosigner)"
                if is_confirmed(
                    await interact(
                        ctx,
                        _show_xpub(xpub, desc=desc_xpub, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                ):
                    return


def show_pubkey(
    ctx: wire.Context, pubkey: str, title: str = "Confirm public key"
) -> Awaitable[None]:
    return confirm_hex(
        ctx,
        br_type="show_pubkey",
        title="Confirm public key",
        data=pubkey,
        br_code=ButtonRequestType.PublicKey,
        icon=ui.ICON_RECEIVE,
    )


async def _show_modal(
    ctx: wire.GenericContext,
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
    text = Text(header, icon, icon_color, new_lines=False)
    if subheader:
        text.bold(subheader)
        text.br()
        text.br_half()
    text.normal(content)
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text, confirm=button_confirm, cancel=button_cancel),
            br_type,
            br_code,
        ),
        exc,
    )


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
    await _show_modal(
        ctx,
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
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "Warning",
    subheader: str | None = None,
    button: str = "Try again",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=br_code,
        header=header,
        subheader=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
        icon=ui.ICON_WRONG,
        icon_color=ui.RED,
    )


def show_success(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Continue",
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=ButtonRequestType.Success,
        header="Success",
        subheader=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
        icon=ui.ICON_CONFIRM,
        icon_color=ui.GREEN,
    )


async def confirm_output(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> None:
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
    text.normal(amount + " to")
    text.mono(*_split_address(address))
    await raise_if_cancelled(
        interact(ctx, Confirm(text), "confirm_output", ButtonRequestType.ConfirmOutput)
    )


async def confirm_decred_sstx_submission(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> None:
    text = Text("Purchase ticket", ui.ICON_SEND, ui.GREEN)
    text.normal(amount)
    text.normal("with voting rights to")
    text.mono(*_split_address(address))
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text),
            "confirm_decred_sstx_submission",
            ButtonRequestType.ConfirmOutput,
        )
    )


async def confirm_hex(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    width: int = MONO_HEX_PER_LINE,
    truncate_middle: bool = False,
) -> None:
    text = Text(title, icon, icon_color, new_lines=False)
    description_lines = 0
    if description is not None:
        description_lines = Span(description, 0, ui.NORMAL).count_lines()
        text.normal(description)
        text.br()
    text.mono(
        *_truncate_hex(
            data,
            lines=TEXT_MAX_LINES - description_lines,
            width=width,
            middle=truncate_middle,
        )
    )
    content: ui.Layout = Confirm(text)
    await raise_if_cancelled(interact(ctx, content, br_type, br_code))


async def confirm_total(
    ctx: wire.GenericContext, total_amount: str, fee_amount: str
) -> None:
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(total_amount)
    text.normal("including fee:")
    text.bold(fee_amount)
    await raise_if_cancelled(
        interact(ctx, HoldToConfirm(text), "confirm_total", ButtonRequestType.SignTx)
    )


async def confirm_joint_total(
    ctx: wire.GenericContext, spending_amount: str, total_amount: str
) -> None:
    text = Text("Joint transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("You are contributing:")
    text.bold(spending_amount)
    text.normal("to the total amount:")
    text.bold(total_amount)
    await raise_if_cancelled(
        interact(
            ctx, HoldToConfirm(text), "confirm_joint_total", ButtonRequestType.SignTx
        )
    )


async def confirm_metadata(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.format_parametrized(content, param if param is not None else "")
    text.br()

    text.normal("Continue?")

    await raise_if_cancelled(interact(ctx, Confirm(text), br_type, br_code))


async def confirm_replacement(
    ctx: wire.GenericContext, description: str, txid: str
) -> None:
    text = Text(description, ui.ICON_SEND, ui.GREEN)
    text.normal("Confirm transaction ID:")
    text.mono(*_truncate_hex(txid, TEXT_MAX_LINES - 1))
    await raise_if_cancelled(
        interact(ctx, Confirm(text), "confirm_replacement", ButtonRequestType.SignTx)
    )


async def confirm_modify_output(
    ctx: wire.GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    page1 = Text("Modify amount", ui.ICON_SEND, ui.GREEN)
    page1.normal("Address:")
    page1.br_half()
    page1.mono(*_split_address(address))

    page2 = Text("Modify amount", ui.ICON_SEND, ui.GREEN)
    if sign < 0:
        page2.normal("Decrease amount by:")
    else:
        page2.normal("Increase amount by:")
    page2.bold(amount_change)
    page2.br_half()
    page2.normal("New amount:")
    page2.bold(amount_new)

    await raise_if_cancelled(
        interact(
            ctx,
            Paginated([page1, Confirm(page2)]),
            "modify_output",
            ButtonRequestType.ConfirmOutput,
        )
    )


async def confirm_modify_fee(
    ctx: wire.GenericContext,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> None:
    text = Text("Modify fee", ui.ICON_SEND, ui.GREEN)
    if sign == 0:
        text.normal("Your fee did not change.")
    else:
        if sign < 0:
            text.normal("Decrease your fee by:")
        else:
            text.normal("Increase your fee by:")
        text.bold(user_fee_change)
    text.br_half()
    text.normal("Transaction fee:")
    text.bold(total_fee_new)
    await raise_if_cancelled(
        interact(ctx, HoldToConfirm(text), "modify_fee", ButtonRequestType.SignTx)
    )


async def confirm_coinjoin(
    ctx: wire.GenericContext, fee_per_anonymity: str | None, total_fee: str
) -> None:
    text = Text("Authorize CoinJoin", ui.ICON_RECOVERY, new_lines=False)
    if fee_per_anonymity is not None:
        text.normal("Fee per anonymity set:\n")
        text.bold("{} %\n".format(fee_per_anonymity))
    text.normal("Maximum total fees:\n")
    text.bold(total_fee)
    await raise_if_cancelled(
        interact(ctx, HoldToConfirm(text), "coinjoin_final", ButtonRequestType.Other)
    )


# TODO cleanup @ redesign
async def confirm_sign_identity(
    ctx: wire.GenericContext, proto: str, identity: str, challenge_visual: str | None
) -> None:
    lines: list[TextContent] = []
    if challenge_visual:
        lines.append(challenge_visual)

    lines.append(ui.MONO)
    lines.extend(chunks(identity, 18))

    text = Text("Sign %s" % proto)
    text.normal(*lines)
    await raise_if_cancelled(
        interact(ctx, Confirm(text), "sign_identity", ButtonRequestType.Other)
    )


async def confirm_signverify(
    ctx: wire.GenericContext, coin: str, message: str, address: str | None = None
) -> None:
    if address:
        header = "Verify {} message".format(coin)
        font = ui.MONO
        br_type = "verify_message"

        text = Text(header)
        text.bold("Confirm address:")
        text.mono(*_split_address(address))
        await raise_if_cancelled(
            interact(ctx, Confirm(text), br_type, ButtonRequestType.Other)
        )
    else:
        header = "Sign {} message".format(coin)
        font = ui.NORMAL
        br_type = "sign_message"

    await raise_if_cancelled(
        interact(
            ctx,
            paginate_text(message, header, font=font),
            br_type,
            ButtonRequestType.Other,
        )
    )
