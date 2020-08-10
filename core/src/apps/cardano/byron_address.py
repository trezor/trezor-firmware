from trezor import log
from trezor.crypto import crc, hashlib

from apps.common import cbor
from apps.common.seed import remove_ed25519_prefix

from .helpers import INVALID_ADDRESS, NETWORK_MISMATCH, protocol_magics

if False:
    from trezor.crypto import bip32
    from . import seed

PROTOCOL_MAGIC_KEY = 2


"""
This is the legacy implementation of Byron addresses. Byron
addresses should however remain supported in Shelley with
exactly the same implementation, thus it is kept here
with base58 encoding and all the nuances of Byron addresses.
"""


def _encode_address_raw(address_data_encoded) -> bytes:
    return cbor.encode(
        [cbor.Tagged(24, address_data_encoded), crc.crc32(address_data_encoded)]
    )


def derive_byron_address(
    keychain: seed.Keychain, path: list, protocol_magic: int
) -> bytes:
    node = keychain.derive(path)

    address_attributes = get_address_attributes(protocol_magic)

    address_root = _get_address_root(node, address_attributes)
    address_type = 0
    address_data = [address_root, address_attributes, address_type]
    address_data_encoded = cbor.encode(address_data)

    return _encode_address_raw(address_data_encoded)


def get_address_attributes(protocol_magic: int) -> dict:
    # protocol magic is included in Byron addresses only on testnets
    if protocol_magics.is_mainnet(protocol_magic):
        address_attributes = {}
    else:
        address_attributes = {PROTOCOL_MAGIC_KEY: cbor.encode(protocol_magic)}

    return address_attributes


def validate_output_byron_address(address: bytes, protocol_magic: int) -> None:
    address_data_encoded = _decode_address_raw(address)
    _validate_address_data_protocol_magic(address_data_encoded, protocol_magic)


def _decode_address_raw(address: bytes) -> bytes:
    try:
        address_unpacked = cbor.decode(address)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise INVALID_ADDRESS

    if not isinstance(address_unpacked, list) or len(address_unpacked) != 2:
        raise INVALID_ADDRESS

    address_data_encoded = address_unpacked[0]
    if not isinstance(address_data_encoded, bytes):
        raise INVALID_ADDRESS

    address_crc = address_unpacked[1]
    if not isinstance(address_crc, int):
        raise INVALID_ADDRESS

    if address_crc != crc.crc32(address_data_encoded):
        raise INVALID_ADDRESS

    return address_data_encoded


def _validate_address_data_protocol_magic(
    address_data_encoded: bytes, protocol_magic: int
) -> None:
    """
    Determines whether the correct protocol magic (or none)
    is included in the address. Addresses on mainnet don't
    contain protocol magic, but addresses on the testnet do.
    """
    address_data = cbor.decode(address_data_encoded)
    if not isinstance(address_data, list) or len(address_data) < 2:
        raise INVALID_ADDRESS

    attributes = address_data[1]
    if protocol_magics.is_mainnet(protocol_magic):
        if PROTOCOL_MAGIC_KEY in attributes:
            raise NETWORK_MISMATCH
    else:  # testnet
        if len(attributes) == 0 or PROTOCOL_MAGIC_KEY not in attributes:
            raise NETWORK_MISMATCH

        protocol_magic_cbor = attributes[PROTOCOL_MAGIC_KEY]
        address_protocol_magic = cbor.decode(protocol_magic_cbor)

        if not isinstance(address_protocol_magic, int):
            raise INVALID_ADDRESS

        if address_protocol_magic != protocol_magic:
            raise NETWORK_MISMATCH


def _address_hash(data: list) -> bytes:
    cbor_data = cbor.encode(data)
    sha_data_hash = hashlib.sha3_256(cbor_data).digest()
    res = hashlib.blake2b(data=sha_data_hash, outlen=28).digest()
    return res


def _get_address_root(node: bip32.HDNode, address_attributes: dict) -> bytes:
    extpubkey = remove_ed25519_prefix(node.public_key()) + node.chain_code()
    return _address_hash([0, [0, extpubkey], address_attributes])
