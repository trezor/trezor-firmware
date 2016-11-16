from trezor import wire, ui
from trezor.utils import unimport

@unimport
async def layout_verify_message(msg, session_id):
    from trezor.messages.Success import Success
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import ripemd160, sha256
    from trezor.crypto import base58
    from ..common import address_type
    from ..common import coins
    from ..common.signtx import node_derive, HashWriter, write_varint

    address = msg.address
    message = msg.message
    signature = msg.signature
    coin_name = getattr(msg, 'coin_name', 'Bitcoin')
    coin = coins.by_name(coin_name)

    ui.display.clear()
    ui.display.text(10, 30, 'Verifying message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, message, ui.MONO, ui.WHITE, ui.BLACK)
    ui.display.text(10, 80, address, ui.MONO, ui.WHITE, ui.BLACK)

    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)

    digest = sha256(h.getvalue()).digest()
    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise ValueError('Invalid signature')

    raw_address = base58.decode_check(address)
    at, pkh = address_type.split(coin, raw_address)
    pkh2 = ripemd160(sha256(pubkey).digest()).digest()

    if pkh != pkh2:
        raise ValueError('Invalid signature')

    return Success(message='Message verified')
