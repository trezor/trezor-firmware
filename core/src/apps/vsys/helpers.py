from trezor.crypto import base58
from trezor.crypto import hashlib

from apps.common import HARDENED
from apps.vsys.constants import VSYS_ADDRESS_VERSION

VSYS_CHECKSUM_LENGTH = 4
VSYS_ADDRESS_HASH_LENGTH = 20
VSYS_ADDRESS_LENGTH = 1 + 1 + VSYS_CHECKSUM_LENGTH + VSYS_ADDRESS_HASH_LENGTH


if bytes == str:  # python2
    str2bytes = lambda s: s
    bytes2str = lambda b: b
    str2list = lambda s: [ord(c) for c in s]
else:  # python3
    str2bytes = lambda s: s.encode('latin-1')
    bytes2str = lambda b: ''.join(map(chr, b))
    str2list = lambda s: [c for c in s]


def keccak256_hash(data=None):
    return hashlib.sha3_256(data=data, keccak=True)


# def keccak_hash(key, msg=None):
#    h = hmac.new(key, msg=msg, digestmod=keccak_factory)
#    return h.digest()


def hash_chain(s):
    a = hashlib.blake2b(s, digest_size=32).digest()
    b = keccak256_hash(a)
    return b


def validate_address(address, chain_id):
    addr = bytes2str(base58.decode(address))
    if addr[0] != chr(VSYS_ADDRESS_VERSION):
        return False  # Wrong address version
    elif addr[1] != chain_id:
        return False  # Wrong chain id
    elif len(addr) != VSYS_ADDRESS_LENGTH:
        return False  # Wrong address length
    elif addr[-VSYS_CHECKSUM_LENGTH:] != hash_chain(str2bytes(addr[:-VSYS_CHECKSUM_LENGTH]))[:VSYS_CHECKSUM_LENGTH]:
        return False  # Wrong address checksum
    else:
        return True


def get_address_from_public_key(public_key, chain_id):
    unhashedAddress = chr(VSYS_ADDRESS_VERSION) + str(chain_id) + hash_chain(public_key)[0:20]
    addressHash = hash_chain(str2bytes(unhashedAddress))[0:4]
    address = bytes2str(base58.encode(str2bytes(unhashedAddress + addressHash)))
    return address


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/360'/a',
    where `a` is an account index from 0 to 1 000 000.
    Additional component added to allow ledger migration
    44'/360'/0'/b' where `b` is an account index from 0 to 1 000 000
    """
    length = len(path)
    if length < 3 or length > 4:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 360 | HARDENED:
        return False
    if length == 3:
        if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
            return False
    if length == 4:
        if path[2] != 0 | HARDENED:
            return False
        if path[3] < HARDENED or path[3] > 1000000 | HARDENED:
            return False
    return True
