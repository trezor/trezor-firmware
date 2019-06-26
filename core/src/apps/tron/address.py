from trezor import log
from trezor.crypto import base58
from trezor.crypto.hashlib import sha3_256

from apps.common import HARDENED, paths


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to fit 44'/195'/a'/0/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 195 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] != 0 and path[3] != 1:
        return False
    if path[4] > 1000000:
        return False
    return True


def get_address_from_public_key(pubkey):
   address = b"\x41" + sha3_256(pubkey[1:65], keccak=True).digest()[12:32]
   return _address_base58(address)

def _address_base58(address):
   return base58.encode_check(address)

def address_to_bytes(address):
   return base58.decode_check(address)

def _b58b(address):
   return base58.encode_check(bytes(address))
