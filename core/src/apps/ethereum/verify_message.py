from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.Success import Success

from apps.common.signverify import require_confirm_verify_message

from .address import address_from_bytes, bytes_from_address
from .sign_message import message_digest


async def verify_message(ctx, msg):
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

    await require_confirm_verify_message(ctx, address, "ETH", msg.message)

    return Success(message="Message verified")
