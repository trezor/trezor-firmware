from micropython import const
from apps.common.confirm import confirm
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.text import Text
from trezor.utils import chunks


async def show_address(ctx, address: str):
    lines = split_address(address)
    content = Text('Confirm address', ui.ICON_RECEIVE, ui.MONO, *lines, icon_color=ui.GREEN)
    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel='QR',
        cancel_style=ui.BTN_KEY)


async def show_qr(ctx, address: str):
    qr_x = const(120)
    qr_y = const(115)
    qr_coef = const(4)

    content = Container(
        Qr(address, (qr_x, qr_y), qr_coef),
        Text('Confirm address', ui.ICON_RECEIVE, ui.MONO, icon_color=ui.GREEN))
    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel='Address',
        cancel_style=ui.BTN_KEY)


def split_address(address: str):
    return chunks(address, 17)
