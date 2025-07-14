from trezor.crypto import base58
from trezor.crypto.hashlib import sha3_256


def address_from_public_key(pubkey: bytes) -> str:
    address_bytes = b"\x41" + sha3_256(pubkey[1:], keccak=True).digest()[12:]
    return base58.encode_check(address_bytes)
