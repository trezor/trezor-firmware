from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_sign_message(msg, session_id):
    from trezor.messages.MessageSignature import MessageSignature
    from trezor.crypto.hashlib import sha256
    from trezor.crypto.curve import secp256k1
    from ..common.signtx import node_derive, HashWriter, write_varint
    from ..common.seed import get_root_node
    from ..common import coins

    ui.display.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, msg.message, ui.MONO, ui.WHITE, ui.BLACK)

    address_n = msg.address_n
    message = msg.message
    coin_name = getattr(msg, 'coin_name', 'Bitcoin')
    coin = coins.by_name(coin_name)

    root = await get_root_node(session_id)
    node = node_derive(root, address_n)
    seckey = node.private_key()
    address = node.address(coin.address_type)

    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)

    digest = sha256(h.getvalue()).digest()

    signature = secp256k1.sign(seckey, digest)

    return MessageSignature(address=address, signature=signature)
