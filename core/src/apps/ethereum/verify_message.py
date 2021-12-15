from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages import Success
from trezor.ui.layouts import confirm_signverify

from apps.common.signverify import decode_message

from .helpers import address_from_bytes, bytes_from_address
from .sign_message import message_digest

if False:
    from trezor.messages import EthereumVerifyMessage
    from trezor.wire import Context


async def verify_message(ctx: Context, msg: EthereumVerifyMessage) -> Success:
    digest = message_digest(msg.message)
    if len(msg.signature) != 65:
        raise wire.DataError("Invalid signature")
    sig = bytearray([msg.signature[64]]) + msg.signature[:64]

    pubkey = secp256k1.verify_recover(sig, digest)

    if not pubkey:
        raise wire.DataError("Invalid signature")

    pkh = sha3_256(pubkey[1:], keccak=True).digest()[-20:]

    address_bytes = bytes_from_address(msg.address)
    if address_bytes != pkh:
        raise wire.DataError("Invalid signature")

    address = address_from_bytes(address_bytes)

    await confirm_signverify(
        ctx, "ETH", decode_message(msg.message), address=address, verify=True
    )

    return Success(message="Message verified")
