from trezor import log
from trezor.crypto import base58, crc, hashlib

from apps.common import cbor
from apps.common.seed import remove_ed25519_prefix

if False:
    from trezor.crypto import bip32
    from typing import Tuple
    from apps.cardano import seed

"""
This is the legacy implementation of Byron addresses (called
bootstrap addresses in Shelley). Bootstrap addresses should
however remain supported in Shelley with exactly the same implementation,
thus it is kept here - with base58 encoding and all the nuances of the
Byron addresses.
"""


def _encode_address_raw(address_data_encoded: bytes) -> str:
    return base58.encode(
        cbor.encode(
            [cbor.Tagged(24, address_data_encoded), crc.crc32(address_data_encoded)]
        )
    )


def derive_address_and_node(
    keychain: seed.Keychain, path: list
) -> Tuple[str, bip32.Node]:
    node = keychain.derive(path)

    address_payload = None
    address_attributes = {}

    address_root = _get_address_root(node, address_payload)
    address_type = 0
    address_data = [address_root, address_attributes, address_type]
    address_data_encoded = cbor.encode(address_data)

    return (_encode_address_raw(address_data_encoded), node)


def is_safe_output_address(address: str) -> bool:
    """
    Determines whether it is safe to include the address as-is as
    a tx output, preventing unintended side effects (e.g. CBOR injection)
    """
    try:
        address_hex = base58.decode(address)
        address_unpacked = cbor.decode(address_hex)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        return False

    if not isinstance(address_unpacked, list) or len(address_unpacked) != 2:
        return False

    address_data_encoded = address_unpacked[0]

    if not isinstance(address_data_encoded, bytes):
        return False

    return _encode_address_raw(address_data_encoded) == address


def _address_hash(data: list) -> bytes:
    data = cbor.encode(data)
    data = hashlib.sha3_256(data).digest()
    res = hashlib.blake2b(data=data, outlen=28).digest()
    return res


def _get_address_root(node: bip32.Node, payload: None) -> bytes:
    extpubkey = remove_ed25519_prefix(node.public_key()) + node.chain_code()
    if payload:
        payload = {1: cbor.encode(payload)}
    else:
        payload = {}
    return _address_hash([0, [0, extpubkey], payload])
