from .validators import *
from apps.common import seed
from apps.common.confirm import confirm
from trezor import ui
from trezor.messages.NEMAddress import NEMAddress
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks


async def nem_get_address(ctx, msg):
    network = validate_network(msg.network)
    node = await seed.derive_node(ctx, msg.address_n, NEM_CURVE)
    address = node.nem_address(network)

    if msg.show_display:
        while True:
            if await _show_address(ctx, address, network):
                break

    return NEMAddress(address=address)


async def _show_address(ctx, address: str, network: int):
    lines = _split_address(address)
    print(network)
    content = Text('Export NEM address', ui.ICON_RECEIVE,
                   ui.MONO, _get_network_str(network) + ' network',
                   ui.MONO, *lines,
                   icon_color=ui.GREEN)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel_style=ui.BTN_KEY)


def _split_address(address: str):
    return chunks(address, 17)


def _get_network_str(network: int) -> str:
    if network == NEM_NETWORK_MAINNET:
        return 'Mainnet'
    elif network == NEM_NETWORK_TESTNET:
        return 'Testnet'
    elif network == NEM_NETWORK_MIJIN:
        return 'Mijin'
