from trezor.crypto import base58, crc, hashlib

from apps.cardano import cbor
from apps.common import HARDENED
from apps.common.seed import remove_ed25519_prefix


def derive_address_and_node(keychain, path: list):
    node = keychain.derive(path)

    address_payload = None
    address_attributes = {}

    address_root = _get_address_root(node, address_payload)
    address_type = 0
    address_data = [address_root, address_attributes, address_type]
    address_data_encoded = cbor.encode(address_data)

    address = base58.encode(
        cbor.encode(
            [cbor.Tagged(24, address_data_encoded), crc.crc32(address_data_encoded)]
        )
    )
    return (address, node)


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to fit 44'/1815'/a'/{0,1}/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    The derivation scheme v1 allowed a'/0/i only,
    but in v2 it can be a'/1/i as well.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1815 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] != 0 and path[3] != 1:
        return False
    if path[4] > 1000000:
        return False
    return True


def _address_hash(data) -> bytes:
    data = cbor.encode(data)
    data = hashlib.sha3_256(data).digest()
    res = hashlib.blake2b(data=data, outlen=28).digest()
    return res


def _get_address_root(node, payload):
    extpubkey = remove_ed25519_prefix(node.public_key()) + node.chain_code()
    if payload:
        payload = {1: cbor.encode(payload)}
    else:
        payload = {}
    return _address_hash([0, [0, extpubkey], payload])
