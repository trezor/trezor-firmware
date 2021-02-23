from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.container import Container
from trezor.ui.loader import LoaderDanger
from trezor.ui.qr import Qr
from trezor.utils import chunks

from ..components.common import break_path_to_lines
from ..components.common.confirm import CONFIRMED
from ..components.tt.button import ButtonCancel, ButtonDefault
from ..components.tt.confirm import Confirm, HoldToConfirm
from ..components.tt.scroll import Paginated
from ..components.tt.text import Text
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
    from typing import Any, Iterator, List, Sequence, Union, Optional

    from trezor import wire
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType

    from . import LayoutType


__all__ = (
    "confirm_action",
    "confirm_wipe",
    "confirm_reset_device",
    "confirm_backup",
    "confirm_path_warning",
    "show_address",
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
)


def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str,
    description: str = None,
    verb: Union[str, bytes] = Confirm.DEFAULT_CONFIRM,
    icon: str = None,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    **kwargs: Any,
) -> LayoutType:
    text = Text(title, icon if icon is not None else ui.ICON_DEFAULT, new_lines=False)
    text.bold(action)
    text.br()
    if description:
        text.normal(description)

    return interact(ctx, Confirm(text, confirm=verb), br_type, br_code)


def confirm_wipe(ctx: wire.GenericContext) -> LayoutType:
    text = Text("Wipe device", ui.ICON_WIPE, ui.RED)
    text.normal("Do you really want to", "wipe the device?", "")
    text.bold("All data will be lost.")
    return interact(
        ctx,
        HoldToConfirm(text, confirm_style=ButtonCancel, loader_style=LoaderDanger),
        "wipe_device",
        ButtonRequestType.WipeDevice,
    )


def confirm_reset_device(ctx: wire.GenericContext, prompt: str) -> LayoutType:
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    text.bold(prompt)
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    return interact(
        ctx,
        Confirm(text, major_confirm=True),
        "setup_device",
        ButtonRequestType.ResetDevice,
    )


async def confirm_backup(ctx: wire.GenericContext) -> bool:
    text1 = Text("Success", ui.ICON_CONFIRM, ui.GREEN)
    text1.bold("New wallet created", "successfully!")
    text1.br_half()
    text1.normal("You should back up your", "new wallet right now.")

    text2 = Text("Warning", ui.ICON_WRONG, ui.RED)
    text2.bold("Are you sure you want", "to skip the backup?")
    text2.br_half()
    text2.normal("You can back up your", "Trezor once, at any time.")

    if (
        await interact(
            ctx,
            Confirm(text1, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
        is CONFIRMED
    ):
        return True

    confirmed = (
        await interact(
            ctx,
            Confirm(text2, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    ) is CONFIRMED
    return confirmed


def confirm_path_warning(ctx: wire.GenericContext, path: str) -> LayoutType:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*break_path_to_lines(path, MONO_CHARS_PER_LINE))
    text.normal("is unknown.", "Are you sure?")
    return interact(
        ctx,
        Confirm(text),
        "path_warning",
        ButtonRequestType.UnknownDerivationPath,
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


def _hex_lines(hex_data: str, lines: int = TEXT_MAX_LINES) -> Iterator[str]:
    if len(hex_data) >= MONO_HEX_PER_LINE * lines:
        hex_data = hex_data[: (MONO_HEX_PER_LINE * lines - 3)] + "..."
    return chunks(hex_data, MONO_HEX_PER_LINE)


def _show_address(
    address: str,
    desc: str,
    network: str = None,
) -> Confirm:
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*_split_address(address))

    return Confirm(text, cancel="QR", cancel_style=ButtonDefault)


def _show_xpub(xpub: str, desc: str, cancel: str) -> Paginated:
    pages: List[ui.Component] = []
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


def show_xpub(
    ctx: wire.GenericContext, xpub: str, desc: str, cancel: str
) -> LayoutType:
    return interact(
        ctx, _show_xpub(xpub, desc, cancel), "show_xpub", ButtonRequestType.PublicKey
    )


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    address_qr: str = None,
    desc: str = "Confirm address",
    network: str = None,
    multisig_index: int = None,
    xpubs: Sequence[str] = [],
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        if (
            await interact(
                ctx,
                _show_address(address, desc, network),
                "show_address",
                ButtonRequestType.Address,
            )
            is CONFIRMED
        ):
            break
        if (
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
            is CONFIRMED
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "Next" if i < len(xpubs) - 1 else "Address"
                desc_xpub = "XPUB #%d" % (i + 1)
                desc_xpub += " (yours)" if i == multisig_index else " (cosigner)"
                if (
                    await interact(
                        ctx,
                        _show_xpub(xpub, desc=desc_xpub, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                    is CONFIRMED
                ):
                    return


# FIXME: this is basically same as confirm_hex
# TODO: pagination for long keys
def show_pubkey(
    ctx: wire.Context, pubkey: str, title: str = "Confirm public key"
) -> LayoutType:
    text = Text(title, ui.ICON_RECEIVE, ui.GREEN)
    text.mono(*_hex_lines(pubkey))
    return interact(ctx, Confirm(text), "show_pubkey", ButtonRequestType.PublicKey)


def show_warning(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: Optional[str] = None,
    button: str = "Try again",
) -> LayoutType:
    text = Text("Warning", ui.ICON_WRONG, ui.RED, new_lines=False)
    if subheader:
        text.bold(subheader)
        text.br()
        text.br_half()
    text.normal(content)
    return interact(
        ctx,
        Confirm(text, confirm=button, cancel=None),
        br_type,
        ButtonRequestType.Warning,
    )


def show_success(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: Optional[str] = None,
    button: str = "Continue",
) -> LayoutType:
    text = Text("Success", ui.ICON_CONFIRM, ui.GREEN, new_lines=False)
    if subheader:
        text.bold(subheader)
        text.br()
        text.br_half()
    text.normal(content)
    return interact(
        ctx,
        Confirm(text, confirm=button, cancel=None),
        br_type,
        ButtonRequestType.Success,
    )


def confirm_output(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> LayoutType:
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
    text.normal(amount + " to")
    text.mono(*_split_address(address))
    return interact(
        ctx, Confirm(text), "confirm_output", ButtonRequestType.ConfirmOutput
    )


def confirm_decred_sstx_submission(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> LayoutType:
    text = Text("Purchase ticket", ui.ICON_SEND, ui.GREEN)
    text.normal(amount)
    text.normal("with voting rights to")
    text.mono(*_split_address(address))
    return interact(
        ctx,
        Confirm(text),
        "confirm_decred_sstx_submission",
        ButtonRequestType.ConfirmOutput,
    )


def confirm_hex(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: str,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.Other,
) -> LayoutType:
    text = Text(title, ui.ICON_SEND, ui.GREEN)
    text.mono(*_hex_lines(data))
    return interact(ctx, Confirm(text), br_type, br_code)


def confirm_total(
    ctx: wire.GenericContext, total_amount: str, fee_amount: str
) -> LayoutType:
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(total_amount)
    text.normal("including fee:")
    text.bold(fee_amount)
    return interact(ctx, HoldToConfirm(text), "confirm_total", ButtonRequestType.SignTx)


def confirm_joint_total(
    ctx: wire.GenericContext, spending_amount: str, total_amount: str
) -> LayoutType:
    text = Text("Joint transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("You are contributing:")
    text.bold(spending_amount)
    text.normal("to the total amount:")
    text.bold(total_amount)
    return interact(
        ctx, HoldToConfirm(text), "confirm_joint_total", ButtonRequestType.SignTx
    )


def confirm_metadata(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    content: str,
    param: Optional[str] = None,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.SignTx,
) -> LayoutType:
    text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.format_parametrized(content, param if param is not None else "")
    text.br()

    text.normal("Continue?")

    return interact(ctx, Confirm(text), br_type, br_code)


def confirm_replacement(
    ctx: wire.GenericContext, description: str, txid: str
) -> LayoutType:
    text = Text(description, ui.ICON_SEND, ui.GREEN)
    text.normal("Confirm transaction ID:")
    text.mono(*_hex_lines(txid, TEXT_MAX_LINES - 1))
    return interact(ctx, Confirm(text), "confirm_replacement", ButtonRequestType.SignTx)


def confirm_modify_output(
    ctx: wire.GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> LayoutType:
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

    return interact(
        ctx,
        Paginated([page1, Confirm(page2)]),
        "modify_output",
        ButtonRequestType.ConfirmOutput,
    )


def confirm_modify_fee(
    ctx: wire.GenericContext,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> LayoutType:
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
    return interact(ctx, HoldToConfirm(text), "modify_fee", ButtonRequestType.SignTx)
