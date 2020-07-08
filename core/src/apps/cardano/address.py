from trezor import wire
from trezor.crypto import base58, hashlib
from trezor.messages import CardanoAddressParametersType, CardanoAddressType

from apps.common import HARDENED
from apps.common.seed import remove_ed25519_prefix

from .byron_address import derive_byron_address, validate_output_byron_address
from .helpers import INVALID_ADDRESS, NETWORK_MISMATCH, purposes
from .helpers.bech32 import bech32_encode
from .helpers.utils import variable_length_encode
from .seed import is_byron_path, is_shelley_path

if False:
    from typing import List
    from trezor.messages import CardanoBlockchainPointerType
    from . import seed

BECH32_ADDRESS_PREFIX = "addr"


def validate_full_path(path: List[int]) -> bool:
    """
    Validates derivation path to fit {44', 1852'}/1815'/a'/{0,1,2}/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    """
    if len(path) != 5:
        return False
    if path[0] != purposes.BYRON and path[0] != purposes.SHELLEY:
        return False
    if path[1] != 1815 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] not in [0, 1, 2]:
        return False
    if path[4] > 1000000:
        return False
    return True


def validate_output_address(
    address: bytes, protocol_magic: int, network_id: int
) -> None:
    if address is None or len(address) == 0:
        raise INVALID_ADDRESS

    if _has_byron_address_header(address):
        validate_output_byron_address(address, protocol_magic)
    elif _has_shelley_address_header(address):
        _validate_address_network_id(address, network_id)
    else:
        raise INVALID_ADDRESS


def _has_byron_address_header(address: bytes) -> bool:
    return (address[0] >> 4) == CardanoAddressType.BYRON


def _has_shelley_address_header(address: bytes) -> bool:
    address_type = address[0] >> 4
    return (
        address_type == CardanoAddressType.BASE
        or address_type == CardanoAddressType.POINTER
        or address_type == CardanoAddressType.ENTERPRISE
        or address_type == CardanoAddressType.REWARD
    )


def _validate_address_network_id(address: bytes, network_id: int) -> None:
    if (address[0] & 0x0F) != network_id:
        raise NETWORK_MISMATCH


def get_public_key_hash(keychain: seed.Keychain, path: List[int]) -> bytes:
    node = keychain.derive(path)
    public_key = remove_ed25519_prefix(node.public_key())
    return hashlib.blake2b(data=public_key, outlen=28).digest()


def get_human_readable_address(address: bytes) -> str:
    if _has_byron_address_header(address):
        return base58.encode(address)
    else:
        return bech32_encode(BECH32_ADDRESS_PREFIX, address)


def derive_human_readable_address(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> str:
    address = derive_address_bytes(keychain, parameters, protocol_magic, network_id)
    return get_human_readable_address(address)


def derive_address_bytes(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> bytes:
    is_byron_address = parameters.address_type == CardanoAddressType.BYRON

    if is_byron_address:
        address = _derive_byron_address(
            keychain, parameters.spending_key_path, protocol_magic
        )
    else:
        address = _derive_shelley_address(keychain, parameters, network_id)

    return address


def _derive_byron_address(
    keychain: seed.Keychain, path: List[int], protocol_magic: int
) -> bytes:
    if not is_byron_path(path):
        raise wire.DataError("Invalid path for byron address!")

    address = derive_byron_address(keychain, path, protocol_magic)
    return address


def _derive_shelley_address(
    keychain: seed.Keychain, parameters: CardanoAddressParametersType, network_id: int,
) -> bytes:
    if not is_shelley_path(parameters.spending_key_path):
        raise wire.DataError("Invalid path for shelley address!")

    address_header = _create_address_header(parameters.address_type, network_id)

    if parameters.address_type == CardanoAddressType.BASE:
        address = _derive_base_address(
            keychain,
            address_header,
            parameters.spending_key_path,
            parameters.staking_key_path,
            parameters.staking_key_hash,
        )
    elif parameters.address_type == CardanoAddressType.ENTERPRISE:
        address = _derive_enterprise_address(
            keychain, address_header, parameters.spending_key_path
        )
    elif parameters.address_type == CardanoAddressType.POINTER:
        address = _derive_pointer_address(
            keychain,
            address_header,
            parameters.spending_key_path,
            parameters.certificate_pointer,
        )
    elif parameters.address_type == CardanoAddressType.REWARD:
        address = _derive_reward_address(
            keychain, address_header, parameters.spending_key_path
        )
    else:
        raise ValueError("Invalid address type '%s'!" % parameters.address_type)

    return address


def _create_address_header(address_type: int, network_id: int) -> bytes:
    if address_type == CardanoAddressType.BYRON:
        """
        Byron addresses don't have an explicit header in the Shelley
        spec. However, thanks to their CBOR structure they always start with
        0b1000 - the byron address id. This is no coincidence.
        The Shelley address headers are purposefully built around these
        starting bits of the byron address.
        """
        raise ValueError("Byron address does not contain an explicit header!")

    if not _validate_address_type(address_type):
        raise ValueError("Invalid address type '%s'!" % address_type)

    header = address_type << 4 | network_id
    return bytes([header])


def _validate_address_type(address_type: int) -> bool:
    return (
        address_type == CardanoAddressType.BYRON
        or address_type == CardanoAddressType.BASE
        or address_type == CardanoAddressType.POINTER
        or address_type == CardanoAddressType.ENTERPRISE
        or address_type == CardanoAddressType.REWARD
    )


def _derive_base_address(
    keychain: seed.Keychain,
    address_header: bytes,
    path: List[int],
    staking_key_path: List[int],
    staking_key_hash: bytes,
) -> bytes:
    spending_key_hash = get_public_key_hash(keychain, path)

    _validate_base_address_staking_info(staking_key_path, staking_key_hash)

    if staking_key_hash is None:
        staking_key_hash = get_public_key_hash(keychain, staking_key_path)

    return address_header + spending_key_hash + staking_key_hash


def _validate_base_address_staking_info(
    staking_key_path: List[int], staking_key_hash: bytes,
) -> None:
    if staking_key_hash is None and staking_key_path is None:
        raise wire.DataError(
            "Base address needs a staking key path or a staking key hash!"
        )

    if staking_key_hash is None and not _is_staking_path(staking_key_path):
        raise wire.DataError("Invalid staking key path!")


def _is_staking_path(path: List[int]) -> bool:
    """
    Validates path to match 1852'/1815'/a'/2/0. Path must
    be a valid Cardano path. It must have a Shelley purpose
    (Byron paths are not valid staking paths), it must have
    2 as chain type and currently there is only one staking
    path for each account so a 0 is required for address index.
    """
    if not validate_full_path(path):
        return False

    if path[0] != purposes.SHELLEY:
        return False
    if path[3] != 2:
        return False
    if path[4] != 0:
        return False

    return True


def _derive_pointer_address(
    keychain: seed.Keychain,
    address_header: bytes,
    path: List[int],
    pointer: CardanoBlockchainPointerType,
) -> bytes:
    spending_key_hash = get_public_key_hash(keychain, path)

    encoded_pointer = _encode_certificate_pointer(pointer)

    return address_header + spending_key_hash + encoded_pointer


def _encode_certificate_pointer(pointer: CardanoBlockchainPointerType) -> bytes:
    if (
        pointer is None
        or pointer.block_index is None
        or pointer.tx_index is None
        or pointer.certificate_index is None
    ):
        raise wire.DataError("Invalid pointer!")

    block_index_encoded = variable_length_encode(pointer.block_index)
    tx_index_encoded = variable_length_encode(pointer.tx_index)
    certificate_index_encoded = variable_length_encode(pointer.certificate_index)

    return bytes(block_index_encoded + tx_index_encoded + certificate_index_encoded)


def _derive_enterprise_address(
    keychain: seed.Keychain, address_header: bytes, path: List[int]
) -> bytes:
    spending_key_hash = get_public_key_hash(keychain, path)

    return address_header + spending_key_hash


def _derive_reward_address(
    keychain: seed.Keychain, address_header: bytes, path: List[int]
) -> bytes:
    if not _is_staking_path(path):
        raise wire.DataError("Invalid path for reward address!")

    staking_key_hash = get_public_key_hash(keychain, path)

    return address_header + staking_key_hash
