from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_get_address(session_id, msg):
    from trezor.messages.Address import Address
    from trezor.messages.FailureType import ProcessError
    from ..common import coins
    from ..common import seed

    if msg.multisig:
        raise wire.FailureError(ProcessError, 'GetAddress.multisig is unsupported')

    address_n = msg.address_n or ()
    coin_name = msg.coin_name or 'Bitcoin'

    node = await seed.get_root(session_id)
    node.derive_path(address_n)
    coin = coins.by_name(coin_name)
    address = node.address(coin.address_type)

    if msg.show_display:
        await _show_address(session_id, address)

    return Address(address=address)


async def _show_address(session_id, address):
    from trezor.messages.ButtonRequestType import Address
    from trezor.ui.text import Text
    from trezor.ui.qr import Qr
    from trezor.ui.container import Container
    from ..common.confirm import require_confirm

    lines = _split_address(address)
    content = Container(
        Qr(address, (120, 135), 3),
        Text('Confirm address', ui.ICON_RESET, ui.MONO, *lines))
    await require_confirm(session_id, content, code=Address)


def _split_address(address):
    from trezor.utils import chunks
    return chunks(address, 17)
