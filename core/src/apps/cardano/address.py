from trezor import wire
from trezor.crypto import base58, hashlib
from trezor.messages import CardanoAddressParametersType, CardanoAddressType

from apps.common import HARDENED
from apps.common.seed import remove_ed25519_prefix

from .byron_address import derive_byron_address, validate_output_byron_address
from .helpers import INVALID_ADDRESS, NETWORK_MISMATCH, bech32, network_ids, purposes
from .helpers.utils import variable_length_encode
from .seed import is_byron_path, is_shelley_path

if False:
    from typing import List
    from trezor.messages import CardanoBlockchainPointerType
    from trezor.messages.CardanoAddressParametersType import EnumTypeCardanoAddressType
    from . import seed

ADDRESS_TYPES_SHELLEY = (
    CardanoAddressType.BASE,
    CardanoAddressType.BASE_SCRIPT_KEY,
    CardanoAddressType.BASE_KEY_SCRIPT,
    CardanoAddressType.BASE_SCRIPT_SCRIPT,
    CardanoAddressType.POINTER,
    CardanoAddressType.POINTER_SCRIPT,
    CardanoAddressType.ENTERPRISE,
    CardanoAddressType.ENTERPRISE_SCRIPT,
    CardanoAddressType.REWARD,
    CardanoAddressType.REWARD_SCRIPT,
)
MIN_ADDRESS_BYTES_LENGTH = 29
MAX_ADDRESS_BYTES_LENGTH = 65


def validate_full_path(path: List[int]) -> bool:
    """
    Validates derivation path to fit {44', 1852'}/1815'/a'/{0,1,2}/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    """
    if len(path) != 5:
        return False
    if path[0] not in (purposes.BYRON, purposes.SHELLEY):
        return False
    if path[1] != 1815 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] not in (0, 1, 2):
        return False
    if path[4] > 1000000:
        return False
    return True


def validate_output_address(address: str, protocol_magic: int, network_id: int) -> None:
    if address is None or len(address) == 0:
        raise INVALID_ADDRESS

    address_bytes = get_address_bytes_unsafe(address)
    address_type = _get_address_type(address_bytes)

    if address_type == CardanoAddressType.BYRON:
        validate_output_byron_address(address_bytes, protocol_magic)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        _validate_output_shelley_address(address, address_bytes, network_id)
    else:
        raise INVALID_ADDRESS


def get_address_bytes_unsafe(address: str) -> bytes:
    try:
        address_bytes = bech32.decode_unsafe(address)
    except ValueError:
        try:
            address_bytes = base58.decode(address)
        except ValueError:
            raise INVALID_ADDRESS

    return address_bytes


def _get_address_type(address: bytes) -> int:
    return address[0] >> 4


def _validate_output_shelley_address(
    address_str: str, address_bytes: bytes, network_id: int
) -> None:
    address_type = _get_address_type(address_bytes)
    # reward address cannot be an output address
    if (
        address_type == CardanoAddressType.REWARD
        or address_type == CardanoAddressType.REWARD_SCRIPT
    ):
        raise INVALID_ADDRESS

    _validate_address_size(address_bytes, address_type)
    _validate_output_address_bech32_hrp(address_str, address_type, network_id)
    _validate_address_network_id(address_bytes, network_id)


def _validate_address_size(
    address_bytes: bytes, address_type: EnumTypeCardanoAddressType
) -> None:
    if not (MIN_ADDRESS_BYTES_LENGTH <= len(address_bytes) <= MAX_ADDRESS_BYTES_LENGTH):
        raise INVALID_ADDRESS


def _validate_output_address_bech32_hrp(
    address_str: str, address_type: EnumTypeCardanoAddressType, network_id: int
) -> None:
    valid_hrp = _get_bech32_hrp_for_address(address_type, network_id)
    bech32_hrp = bech32.get_hrp(address_str)

    if valid_hrp != bech32_hrp:
        raise INVALID_ADDRESS


def _get_bech32_hrp_for_address(
    address_type: EnumTypeCardanoAddressType, network_id: int
) -> str:
    if address_type == CardanoAddressType.BYRON:
        # Byron address uses base58 encoding
        raise ValueError

    if address_type == CardanoAddressType.REWARD:
        if network_ids.is_mainnet(network_id):
            return bech32.HRP_REWARD_ADDRESS
        else:
            return bech32.HRP_TESTNET_REWARD_ADDRESS
    else:
        if network_ids.is_mainnet(network_id):
            return bech32.HRP_ADDRESS
        else:
            return bech32.HRP_TESTNET_ADDRESS


def _validate_address_network_id(address: bytes, network_id: int) -> None:
    if _get_address_network_id(address) != network_id:
        raise NETWORK_MISMATCH


def _get_address_network_id(address: bytes) -> int:
    return address[0] & 0x0F


def get_public_key_hash(keychain: seed.Keychain, path: List[int]) -> bytes:
    node = keychain.derive(path)
    public_key = remove_ed25519_prefix(node.public_key())
    return hashlib.blake2b(data=public_key, outlen=28).digest()


def derive_human_readable_address(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> str:
    address = derive_address_bytes(keychain, parameters, protocol_magic, network_id)

    address_type = _get_address_type(address)
    if address_type == CardanoAddressType.BYRON:
        return base58.encode(address)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        hrp = _get_bech32_hrp_for_address(_get_address_type(address), network_id)
        return bech32.encode(hrp, address)
    else:
        raise ValueError


def derive_address_bytes(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> bytes:
    is_byron_address = parameters.address_type == CardanoAddressType.BYRON

    if is_byron_address:
        address = _derive_byron_address(keychain, parameters.address_n, protocol_magic)
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
    if not is_shelley_path(parameters.address_n):
        raise wire.DataError("Invalid path for shelley address!")

    if parameters.address_type == CardanoAddressType.BASE:
        address = _derive_base_address(
            keychain,
            parameters.address_n,
            parameters.address_n_staking,
            parameters.staking_key_hash,
            network_id,
        )
    elif parameters.address_type == CardanoAddressType.ENTERPRISE:
        address = _derive_enterprise_address(keychain, parameters.address_n, network_id)
    elif parameters.address_type == CardanoAddressType.POINTER:
        address = _derive_pointer_address(
            keychain, parameters.address_n, parameters.certificate_pointer, network_id,
        )
    elif parameters.address_type == CardanoAddressType.REWARD:
        address = _derive_reward_address(keychain, parameters.address_n, network_id)
    else:
        raise wire.DataError("Invalid address type!")

    return address


def _create_address_header(
    address_type: EnumTypeCardanoAddressType, network_id: int
) -> bytes:
    header = address_type << 4 | network_id
    return header.to_bytes(1, "little")


def _derive_base_address(
    keychain: seed.Keychain,
    path: List[int],
    staking_path: List[int],
    staking_key_hash: bytes,
    network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.BASE, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)

    _validate_base_address_staking_info(staking_path, staking_key_hash)

    if staking_key_hash is None:
        staking_key_hash = get_public_key_hash(keychain, staking_path)

    return header + spending_key_hash + staking_key_hash


def _validate_base_address_staking_info(
    staking_path: List[int], staking_key_hash: bytes,
) -> None:
    if (staking_key_hash is None) == (not staking_path):
        raise wire.DataError(
            "Base address needs either a staking path or a staking key hash!"
        )

    if staking_key_hash is None and not is_staking_path(staking_path):
        raise wire.DataError("Invalid staking path!")


def is_staking_path(path: List[int]) -> bool:
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
    path: List[int],
    pointer: CardanoBlockchainPointerType,
    network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.POINTER, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)
    encoded_pointer = _encode_certificate_pointer(pointer)

    return header + spending_key_hash + encoded_pointer


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
    keychain: seed.Keychain, path: List[int], network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.ENTERPRISE, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)

    return header + spending_key_hash


def _derive_reward_address(
    keychain: seed.Keychain, path: List[int], network_id: int,
) -> bytes:
    if not is_staking_path(path):
        raise wire.DataError("Invalid path for reward address!")

    header = _create_address_header(CardanoAddressType.REWARD, network_id)
    staking_key_hash = get_public_key_hash(keychain, path)

    return header + staking_key_hash
