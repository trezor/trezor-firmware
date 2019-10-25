from trezor.crypto import base58
from trezor.crypto import hashlib
from trezor.crypto.curve import curve25519

from apps.common import HARDENED
from apps.vsys.constants import VSYS_ADDRESS_VERSION

VSYS_CHECKSUM_LENGTH = 4
VSYS_ADDRESS_HASH_LENGTH = 20
VSYS_ADDRESS_LENGTH = 1 + 1 + VSYS_CHECKSUM_LENGTH + VSYS_ADDRESS_HASH_LENGTH


def keccak256_hash(data=None):
    return hashlib.sha3_256(data=data, keccak=True)


def hash_chain(s: bytes):
    a = hashlib.blake2b(s, outlen=32).digest()
    b = keccak256_hash(a).digest()
    return b


def validate_address(address: str, chain_id: str):
    try:
        addr_bytes = base58.decode(address)
    except:
        return False
    if len(addr_bytes) != VSYS_ADDRESS_LENGTH:
        return False  # Wrong address length
    elif addr_bytes[0] != VSYS_ADDRESS_VERSION:
        return False  # Wrong address version
    elif not chain_id or chr(addr_bytes[1]) != chain_id[0]:
        return False  # Wrong chain id
    else:
        expected_checksum = addr_bytes[-VSYS_CHECKSUM_LENGTH:]
        actual_checksum = hash_chain(addr_bytes[:-VSYS_CHECKSUM_LENGTH])[:VSYS_CHECKSUM_LENGTH]
        return expected_checksum == actual_checksum


def get_address_from_public_key(public_key: str, chain_id: str):
    addr_head_bytes = bytes([VSYS_ADDRESS_VERSION] + [ord(c) for c in chain_id])
    addr_body_bytes = hash_chain(base58.decode(public_key))[:VSYS_ADDRESS_HASH_LENGTH]
    unhashed_address = addr_head_bytes + addr_body_bytes
    address_hash = hash_chain(unhashed_address)[:VSYS_CHECKSUM_LENGTH]
    address = base58.encode(unhashed_address + address_hash)
    return address


def modify_private_key(private_key: bytes):
    sk = list(private_key)
    sk[0] &= 248
    sk[31] = (sk[31] & 127) | 64
    return bytes(sk)


def get_public_key_from_private_key(private_key: str):
    private_key_bytes = base58.decode(private_key)
    public_key_bytes = curve25519.publickey(private_key_bytes)
    public_key = base58.encode(public_key_bytes)
    return public_key


def get_chain_id(path: list) -> str:
    return "M" if len(path) >= 3 and path[1] == 360 | HARDENED else "T"


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/360'/a',
    where `a` is an account index from 0 to 1 000 000.
    """
    if len(path) != 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 360 | HARDENED and path[1] != 1 | HARDENED :
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    return True


def convert_to_nano_sec(timestamp):
    if timestamp < 1e10:
        return timestamp * 1e9
    elif timestamp < 1e13:
        return timestamp * 1e6
    elif timestamp < 1e16:
        return timestamp * 1e3
    else:
        return timestamp