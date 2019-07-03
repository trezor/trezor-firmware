from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.button import ButtonDefault
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common import HARDENED
from apps.common.confirm import confirm, require_confirm

if False:
    from typing import Iterable
    from trezor import wire


async def show_address(
    ctx: wire.Context, address: str, desc: str = "Confirm address", network: str = None
) -> bool:
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*split_address(address))

    return await confirm(
        ctx,
        text,
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


async def show_qr(
    ctx: wire.Context, address: str, desc: str = "Confirm address"
) -> bool:
    QR_X = const(120)
    QR_Y = const(115)
    QR_COEF = const(4)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    content = Container(qr, text)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel="Address",
        cancel_style=ButtonDefault,
    )


async def show_pubkey(ctx: wire.Context, pubkey: bytes) -> None:
    lines = chunks(hexlify(pubkey).decode(), 18)
    text = Text("Confirm public key", ui.ICON_RECEIVE, ui.GREEN)
    text.mono(*lines)
    await require_confirm(ctx, text, ButtonRequestType.PublicKey)


def split_address(address: str) -> Iterable[str]:
    return chunks(address, 17)


def address_n_to_str(address_n: list) -> str:
    def path_item(i: int) -> str:
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    if not address_n:
        return "m"

    return "m/" + "/".join([path_item(i) for i in address_n])
