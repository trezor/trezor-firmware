from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_sign_message(msg, session_id):
    from trezor.messages.MessageSignature import MessageSignature
    from trezor.crypto.curve import secp256k1
    from ..common.seed import get_node
    from ..common import coins
    from ..common.signverify import message_digest

    ui.display.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, msg.message, ui.MONO, ui.WHITE, ui.BLACK)

    coin_name = getattr(msg, 'coin_name', 'Bitcoin')
    coin = coins.by_name(coin_name)

    node = await get_node(session_id, msg.address_n)
    seckey = node.private_key()
    address = node.address(coin.address_type)

    digest = message_digest(coin, msg.message)

    signature = secp256k1.sign(seckey, digest)

    return MessageSignature(address=address, signature=signature)
