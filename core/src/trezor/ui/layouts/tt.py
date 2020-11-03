from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.container import Container
from trezor.ui.loader import LoaderDanger
from trezor.ui.qr import Qr
from trezor.utils import chunks

from .common import interact
from ..components.common import break_path_to_lines
from ..components.common.confirm import CONFIRMED
from ..components.tt.button import ButtonCancel, ButtonDefault
from ..components.tt.confirm import Confirm, HoldToConfirm
from ..components.tt.scroll import Paginated
from ..components.tt.text import Text

if False:
    from typing import Iterator, Iterable, List, Sequence, Union

    from trezor import wire
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType

    from . import LayoutType


def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str = None,
    description: str = None,
    verb: Union[str, bytes] = Confirm.DEFAULT_CONFIRM,
    icon: str = None,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    **kwargs,
) -> LayoutType:
    text = Text(title, icon if icon is not None else ui.ICON_CONFIRM, new_lines=False)
    if action:
        for line in action:
            text.bold(line)
            text.br()
        if not kwargs.get("compact", False):
            text.br_half()
    if description:
        for line in description:
            text.normal(line)
            text.br()

    return interact(ctx, Confirm(text, confirm=verb), br_type, br_code)


def confirm_wipe(ctx: wire.GenericContext) -> LayoutType:
    text = Text("Wipe device", ui.ICON_WIPE, ui.RED)
    text.normal("Do you really want to", "wipe the device?", "")
    text.bold("All data will be lost.")
    return interact(
        ctx,
        HoldToConfirm(text, confirm_style=ButtonCancel, loader_style=LoaderDanger),
        "confirm_wipe",
        ButtonRequestType.WipeDevice,
    )


def confirm_reset_device(ctx: wire.GenericContext, prompt: str) -> LayoutType:
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    for line in prompt:
        text.bold(line)
        text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    return interact(
        ctx,
        Confirm(text, major_confirm=True),
        "confirm_setup",
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
            "confirm_backup",
            ButtonRequestType.ResetDevice,
        )
        is CONFIRMED
    ):
        return True

    confirmed = (
        await interact(
            ctx,
            Confirm(text2, cancel="Skip", confirm="Back up", major_confirm=True),
            "confirm_backup",
            ButtonRequestType.ResetDevice,
        )
    ) is CONFIRMED
    return confirmed


def confirm_path_warning(ctx: wire.GenericContext, path: str) -> LayoutType:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*break_path_to_lines(path, 17))
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
    QR_X = const(120)
    QR_Y = const(115)
    QR_SIZE_THRESHOLD = const(63)
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)

    return Confirm(Container(qr, text), cancel=cancel, cancel_style=ButtonDefault)


def _split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)  # 18 on T1


def _hex_lines(data: bytes) -> Iterator[str]:
    hex_data = hexlify(data).decode()
    if len(hex_data) >= 18 * 5:
        hex_data = hex_data[: (18 * 5 - 3)] + "..."
    return chunks(hex_data, 18)


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
    pages = []  # type: List[ui.Component]
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
            )
            is CONFIRMED
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "Next" if i < len(xpubs) - 1 else "Address"
                desc = "XPUB #%d" % (i + 1)
                desc += " (yours)" if i == multisig_index else " (others)"
                if (
                    await interact(
                        ctx,
                        _show_xpub(xpub, desc=desc, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                    is CONFIRMED
                ):
                    return


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


def confirm_hex(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: bytes,
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
    param: str = "",
    br_code: EnumTypeButtonRequestType = ButtonRequestType.SignTx,
) -> LayoutType:
    text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.format_parametrized(content, param)
    if text.count_lines() <= 3:
        text.br_half()

    text.normal("Continue?")

    return interact(ctx, Confirm(text), br_type, br_code)
