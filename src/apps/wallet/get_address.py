from micropython import const
from trezor import ui
from trezor.messages import ButtonRequestType, InputScriptType
from trezor.messages.Address import Address
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.text import Text
from trezor.utils import chunks
from apps.common import coins, seed
from apps.common.confirm import confirm
from apps.wallet.sign_tx import addresses


async def get_address(ctx, msg):
    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    node = await seed.derive_node(ctx, msg.address_n)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    address_short = address[len(coin.cashaddr_prefix) + 1:] if coin.cashaddr_prefix is not None else address

    if msg.show_display:
        while True:
            if await _show_address(ctx, address_short):
                break
            if await _show_qr(ctx, address.upper() if msg.script_type == InputScriptType.SPENDWITNESS else address):
                break

    return Address(address=address)


async def _show_address(ctx, address: str):
    lines = _split_address(address)
    content = Text('Confirm address', ui.ICON_RECEIVE, ui.MONO, *lines, icon_color=ui.GREEN)
    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel='QR',
        cancel_style=ui.BTN_KEY)


async def _show_qr(ctx, address: str):
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


def _split_address(address: str):
    return chunks(address, 17)
