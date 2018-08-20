from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEMAddress import NEMAddress
from trezor.ui.text import Text

from .helpers import NEM_CURVE, get_network_str
from .layout import split_address
from .validators import validate_network

from apps.common import seed
from apps.common.confirm import confirm
from apps.common.show import show_qr


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
    text = Text("Confirm address", ui.ICON_RECEIVE, icon_color=ui.GREEN)
    text.normal("%s network" % get_network_str(network))
    text.mono(*lines)
    return await confirm(
        ctx, text, code=ButtonRequestType.Address, cancel="QR", cancel_style=ui.BTN_KEY
    )
