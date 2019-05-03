from ubinascii import hexlify, unhexlify

from . import helpers, serialize

from trezor.crypto import der
from trezor.crypto.hashlib import sha256
from trezor.crypto.curve import secp256k1


def generate_content_signature(json: bytes, private_key: bytes) -> bytes:
    msghash = sha256(json).digest()
    return secp256k1.sign(private_key, msghash)

def verify_content_signature(public_key: bytes, signature: bytes, unsigned_data: bytes ) -> bool:
    msghash = sha256(unsigned_data).digest()
    return secp256k1.verify(public_key, signature, msghash)
