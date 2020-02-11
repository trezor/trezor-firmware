from trezor.crypto import base58
from trezor.crypto.scripts import sha256_ripemd160_digest

from apps.common import HARDENED

CURVE = "nist256p1"


def get_address_from_public_key(pubkey: bytes) -> str:
    """
    Computes address from public key
    """
    address_bytes = b"\x17" + sha256_ripemd160_digest(b"\x21" + pubkey + b"\xac")
    return base58.encode_check(address_bytes)


def get_bytes_from_address(address: str) -> bytes:
    """
    Converts base58check address to hex representation
    """
    return base58.decode_check(address)[1:]


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to fit 44'/1024'/a'/{0,1}/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    The derivation scheme v1 allowed a'/0/i only,
    but in v2 it can be a'/1/i as well.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1024 | HARDENED and path[1] != 888 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] != 0 and path[3] != 1:
        return False
    if path[4] > 1000000:
        return False
    return True
