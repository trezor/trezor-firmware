from trezor import ui
from trezor.utils import unimport


def cipher_key_value(msg, seckey: bytes) -> bytes:
    from trezor.crypto.hashlib import sha512
    from trezor.crypto import hmac
    from trezor.crypto.aes import AES_CBC_Encrypt, AES_CBC_Decrypt

    data = msg.key
    data += 'E1' if msg.ask_on_encrypt else 'E0'
    data += 'D1' if msg.ask_on_decrypt else 'D0'
    data = hmac.new(seckey, data, sha512).digest()
    key = data[:32]
    if msg.iv and len(msg.iv) == 16:
        iv = msg.iv
    else:
        iv = data[32:48]

    if msg.encrypt:
        aes = AES_CBC_Encrypt(key=key, iv=iv)
    else:
        aes = AES_CBC_Decrypt(key=key, iv=iv)

    return aes.update(msg.value)


@unimport
async def layout_cipher_key_value(session_id, msg):
    from trezor.messages.CipheredKeyValue import CipheredKeyValue
    from ..common import seed

    if len(msg.value) % 16 > 0:
        raise ValueError('Value length must be a multiple of 16')

    ui.display.clear()
    ui.display.text(10, 30, 'CipherKeyValue',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, msg.key, ui.MONO, ui.WHITE, ui.BLACK)

    node = await seed.get_root(session_id)
    node.derive_path(msg.address_n)

    value = cipher_key_value(msg, node.private_key())

    return CipheredKeyValue(value=value)
