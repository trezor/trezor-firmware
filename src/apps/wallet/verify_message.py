from trezor import ui


async def layout_verify_message(ctx, msg):
    from trezor.messages.Success import Success
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import ripemd160, sha256
    from trezor.crypto import base58
    from ..common import address_type
    from ..common import coins
    from ..common.signverify import message_digest

    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    digest = message_digest(coin, msg.message)
    pubkey = secp256k1.verify_recover(msg.signature, digest)

    if not pubkey:
        raise ValueError('Invalid signature')

    raw_address = base58.decode_check(msg.address)
    at, pkh = address_type.split(coin, raw_address)
    pkh2 = ripemd160(sha256(pubkey).digest()).digest()

    if pkh != pkh2:
        raise ValueError('Invalid signature')

    ui.display.clear()
    ui.display.text(10, 30, 'Verifying message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BG)
    ui.display.text(10, 60, msg.message, ui.MONO, ui.FG, ui.BG)
    ui.display.text(10, 80, msg.address, ui.MONO, ui.FG, ui.BG)

    return Success(message='Message verified')
