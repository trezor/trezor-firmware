from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_ethereum_get_address(session_id, msg):
    from trezor.messages.EthereumAddress import EthereumAddress
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from ..common.seed import get_node

    address_n = msg.address_n or ()

    node = await get_node(session_id, address_n)

    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False) # uncompressed
    address = sha3_256(public_key[1:]).digest(True)[12:] # Keccak

    if msg.show_display:
        await _show_address(session_id, address)
    return EthereumAddress(address=address)


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
    return chunks(address, 20)
