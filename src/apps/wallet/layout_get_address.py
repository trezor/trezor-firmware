from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_get_address(message, session_id):
    from trezor.messages.Address import Address
    from trezor.messages.FailureType import Other
    from ..common.seed import get_node

    address_n = getattr(message, 'address_n', ())
    coin_name = getattr(message, 'coin_name', None)
    multisig = getattr(message, 'multisig', None)
    show_display = getattr(message, 'show_display', False)

    # TODO: support custom coin addresses
    # TODO: support multisig addresses

    if coin_name != 'Bitcoin':
        raise wire.FailureError(Other, 'GetAddress.coin_name is unsupported')
    if multisig:
        raise wire.FailureError(Other, 'GetAddress.multisig is unsupported')

    node = await get_node(session_id, address_n)

    address_version = 0
    address = node.address(address_version)

    if show_display:
        await _show_address(session_id, address)
    return Address(address=address)


async def _show_address(session_id, address):
    from trezor.messages.ButtonRequestType import Address
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm

    content = Text('Confirm address', ui.ICON_RESET,
                   ui.MONO, *_split_address(address))
    await require_confirm(session_id, content, code=Address)


def _split_address(address):
    from trezor.utils import chunks
    return chunks(address, 17)
