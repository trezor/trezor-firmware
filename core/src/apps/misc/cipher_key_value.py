from trezor import wire
from trezor.crypto import aes, hmac
from trezor.messages.CipheredKeyValue import CipheredKeyValue
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm
from apps.common.keychain import get_keychain
from apps.common.paths import AlwaysMatchingSchema


async def cipher_key_value(ctx, msg):
    keychain = await get_keychain(ctx, "secp256k1", [AlwaysMatchingSchema])

    if len(msg.value) % 16 > 0:
        raise wire.DataError("Value length must be a multiple of 16")

    encrypt = msg.encrypt
    decrypt = not msg.encrypt
    if (encrypt and msg.ask_on_encrypt) or (decrypt and msg.ask_on_decrypt):
        if encrypt:
            title = "Encrypt value"
        else:
            title = "Decrypt value"
        text = Text(title)
        text.normal(msg.key)
        await require_confirm(ctx, text)

    node = keychain.derive(msg.address_n)
    value = compute_cipher_key_value(msg, node.private_key())
    return CipheredKeyValue(value=value)


def compute_cipher_key_value(msg, seckey: bytes) -> bytes:
    data = msg.key
    data += "E1" if msg.ask_on_encrypt else "E0"
    data += "D1" if msg.ask_on_decrypt else "D0"
    data = hmac(hmac.SHA512, seckey, data).digest()
    key = data[:32]
    if msg.iv and len(msg.iv) == 16:
        iv = msg.iv
    else:
        iv = data[32:48]

    ctx = aes(aes.CBC, key, iv)
    if msg.encrypt:
        return ctx.encrypt(msg.value)
    else:
        return ctx.decrypt(msg.value)
