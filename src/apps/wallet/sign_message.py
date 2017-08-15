from trezor import ui
from trezor.utils import unimport


@unimport
async def layout_sign_message(ctx, msg):
    from trezor.messages.MessageSignature import MessageSignature
    from trezor.crypto.curve import secp256k1
    from ..common import coins
    from ..common import seed
    from ..common.signverify import message_digest

    ui.display.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, msg.message, ui.MONO, ui.WHITE, ui.BLACK)

    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    node = await seed.get_root(ctx)
    node.derive_path(msg.address_n)

    seckey = node.private_key()
    address = node.address(coin.address_type)

    digest = message_digest(coin, msg.message)

    signature = secp256k1.sign(seckey, digest)

    return MessageSignature(address=address, signature=signature)
