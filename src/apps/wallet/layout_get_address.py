from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_get_address(msg, session_id):
    from trezor.messages.Address import Address
    from trezor.messages.FailureType import Other
    from ..common.seed import get_node
    from ..common import coins

    address_n = getattr(msg, 'address_n', ())
    coin_name = getattr(msg, 'coin_name', 'Bitcoin')
    multisig = getattr(msg, 'multisig', None)
    show_display = getattr(msg, 'show_display', False)

    # TODO: support multisig addresses

    if multisig:
        raise wire.FailureError(Other, 'GetAddress.multisig is unsupported')

    node = await get_node(session_id, address_n)

    coin = coins.by_name(coin_name)
    address = node.address(coin.address_type)

    if show_display:
        await _show_address(session_id, address)
    return Address(address=address)


async def _show_address(session_id, address):
    from trezor.messages.ButtonRequestType import Address
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm

    # TODO: qr code

    content = Text('Confirm address', ui.ICON_RESET,
                   ui.MONO, *_split_address(address))
    await require_confirm(session_id, content, code=Address)


def _split_address(address):
    from trezor.utils import chunks
    return chunks(address, 17)
