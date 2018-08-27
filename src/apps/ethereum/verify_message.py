from ubinascii import hexlify

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address
from apps.common.signverify import split_message
from apps.ethereum.sign_message import message_digest


async def verify_message(ctx, msg):
    digest = message_digest(msg.message)
    sig = bytearray([msg.signature[64]]) + msg.signature[:64]
    pubkey = secp256k1.verify_recover(sig, digest)

    if not pubkey:
        raise ValueError("Invalid signature")

    pkh = sha3_256(pubkey[1:], keccak=True).digest()[-20:]

    if msg.address != pkh:
        raise ValueError("Invalid signature")

    address = "0x" + hexlify(msg.address).decode()

    await require_confirm_verify_message(ctx, address, msg.message)

    return Success(message="Message verified")


async def require_confirm_verify_message(ctx, address, message):
    text = Text("Confirm address")
    text.mono(*split_address(address))
    await require_confirm(ctx, text)

    text = Text("Verify message")
    text.mono(*split_message(message))
    await require_confirm(ctx, text)
