from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEMAddress import NEMAddress
from trezor.ui.text import Text

from apps.common import seed
from apps.common.confirm import confirm
from apps.common.display_address import show_qr

from .layout import split_address
from .helpers import get_network_str, NEM_CURVE
from .validators import validate_network


async def get_address(ctx, msg):
    network = validate_network(msg.network)
    node = await seed.derive_node(ctx, msg.address_n, NEM_CURVE)
    address = node.nem_address(network)

    if msg.show_display:

        while True:
            if await _show_address(ctx, address, network):
                break
            if await show_qr(ctx, address.upper()):
                break

    return NEMAddress(address=address)


async def _show_address(ctx, address: str, network: int):
    lines = split_address(address)
    content = Text(
        'Confirm address', ui.ICON_RECEIVE,
        ui.NORMAL, '%s network' % get_network_str(network),
        ui.MONO, *lines,
        icon_color=ui.GREEN)
    return await confirm(
            ctx,
            content,
            code=ButtonRequestType.Address,
            cancel='QR',
            cancel_style=ui.BTN_KEY)
