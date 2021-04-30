from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.button import ButtonDefault
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import TEXT_MAX_LINES, Span, Text
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.utils import chunks

from apps.common import HARDENED
from apps.common.confirm import confirm

if False:
    from typing import Iterable, Iterator
    from trezor import wire


async def show_qr(
    ctx: wire.Context,
    address: str,
    desc: str = "Confirm address",
    cancel: str = "Address",
) -> bool:
    QR_X = const(120)
    QR_Y = const(115)
    QR_SIZE_THRESHOLD = const(63)
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    content = Container(qr, text)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel=cancel,
        cancel_style=ButtonDefault,
    )


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


def address_n_to_str(address_n: Iterable[int]) -> str:
    def path_item(i: int) -> str:
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    if not address_n:
        return "m"

    return "m/" + "/".join([path_item(i) for i in address_n])


async def show_warning(
    ctx: wire.GenericContext,
    content: Iterable[str],
    subheader: Iterable[str] = [],
    button: str = "Try again",
) -> None:
    text = Text("Warning", ui.ICON_WRONG, ui.RED)
    if subheader:
        for row in subheader:
            text.bold(row)
        text.br_half()
    for row in content:
        text.normal(row)
    await require_confirm(
        ctx, text, ButtonRequestType.Warning, confirm=button, cancel=None
    )


async def show_success(
    ctx: wire.GenericContext,
    content: Iterable[str] = [],
    subheader: Iterable[str] = [],
    button: str = "Continue",
) -> None:
    text = Text("Success", ui.ICON_CONFIRM, ui.GREEN)
    if subheader:
        for row in subheader:
            text.bold(row)
        text.br_half()
    for row in content:
        text.normal(row)
    await require_confirm(
        ctx, text, ButtonRequestType.Success, confirm=button, cancel=None
    )
