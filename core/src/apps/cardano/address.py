from trezor.crypto import base58, hashlib
from trezor.enums import CardanoAddressType

from .byron_address import derive_byron_address, validate_byron_address
from .helpers import (
    ADDRESS_KEY_HASH_SIZE,
    INVALID_ADDRESS,
    INVALID_ADDRESS_PARAMETERS,
    NETWORK_MISMATCH,
    bech32,
    network_ids,
)
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .helpers.utils import derive_public_key, variable_length_encode
from .seed import is_byron_path, is_shelley_path

if False:
    from trezor.messages import (
        CardanoBlockchainPointerType,
        CardanoAddressParametersType,
    )
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


def validate_address_parameters(parameters: CardanoAddressParametersType) -> None:
    _validate_address_parameters_structure(parameters)

    if parameters.address_type == CardanoAddressType.BYRON:
        if not is_byron_path(parameters.address_n):
            raise INVALID_ADDRESS_PARAMETERS
    elif parameters.address_type in ADDRESS_TYPES_SHELLEY:
        if not is_shelley_path(parameters.address_n):
            raise INVALID_ADDRESS_PARAMETERS

        if parameters.address_type == CardanoAddressType.BASE:
            _validate_base_address_staking_info(
                parameters.address_n_staking, parameters.staking_key_hash
            )
        elif parameters.address_type == CardanoAddressType.POINTER:
            if parameters.certificate_pointer is None:
                raise INVALID_ADDRESS_PARAMETERS
        elif parameters.address_type == CardanoAddressType.REWARD:
            if not SCHEMA_STAKING_ANY_ACCOUNT.match(parameters.address_n):
                raise INVALID_ADDRESS_PARAMETERS
    else:
        raise INVALID_ADDRESS_PARAMETERS


def _validate_address_parameters_structure(
    parameters: CardanoAddressParametersType,
) -> None:
    address_n_staking = parameters.address_n_staking
    staking_key_hash = parameters.staking_key_hash
    certificate_pointer = parameters.certificate_pointer

    fields_to_be_empty: tuple = ()
    if parameters.address_type in (
        CardanoAddressType.BYRON,
        CardanoAddressType.REWARD,
        CardanoAddressType.ENTERPRISE,
    ):
        fields_to_be_empty = (address_n_staking, staking_key_hash, certificate_pointer)
    elif parameters.address_type == CardanoAddressType.BASE:
        fields_to_be_empty = (certificate_pointer,)
    elif parameters.address_type == CardanoAddressType.POINTER:
        fields_to_be_empty = (address_n_staking, staking_key_hash)

    if any(fields_to_be_empty):
        raise INVALID_ADDRESS_PARAMETERS


def _validate_base_address_staking_info(
    staking_path: list[int],
    staking_key_hash: bytes | None,
) -> None:
    if staking_key_hash and staking_path:
        raise INVALID_ADDRESS_PARAMETERS

    if staking_key_hash:
        if len(staking_key_hash) != ADDRESS_KEY_HASH_SIZE:
            raise INVALID_ADDRESS_PARAMETERS
    elif staking_path:
        if not SCHEMA_STAKING_ANY_ACCOUNT.match(staking_path):
            raise INVALID_ADDRESS_PARAMETERS
    else:
        raise INVALID_ADDRESS_PARAMETERS


def _validate_address_and_get_type(
    address: str, protocol_magic: int, network_id: int
) -> int:
    """
    Validates Cardano address and returns its type
    for the convenience of outward-facing functions.
    """
    if address is None or len(address) == 0:
        raise INVALID_ADDRESS

    address_bytes = get_address_bytes_unsafe(address)
    address_type = _get_address_type(address_bytes)

    if address_type == CardanoAddressType.BYRON:
        validate_byron_address(address_bytes, protocol_magic)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        _validate_shelley_address(address, address_bytes, network_id)
    else:
        raise INVALID_ADDRESS

    return address_type


def validate_output_address(address: str, protocol_magic: int, network_id: int) -> None:
    address_type = _validate_address_and_get_type(address, protocol_magic, network_id)

    if address_type in (CardanoAddressType.REWARD, CardanoAddressType.REWARD_SCRIPT):
        raise INVALID_ADDRESS


def validate_reward_address(address: str, protocol_magic: int, network_id: int) -> None:
    address_type = _validate_address_and_get_type(address, protocol_magic, network_id)

    if address_type not in (
        CardanoAddressType.REWARD,
        CardanoAddressType.REWARD_SCRIPT,
    ):
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


def _get_address_type(address: bytes) -> CardanoAddressType:
    return address[0] >> 4  # type: ignore


def _validate_shelley_address(
    address_str: str, address_bytes: bytes, network_id: int
) -> None:
    address_type = _get_address_type(address_bytes)

    _validate_address_size(address_bytes)
    _validate_address_bech32_hrp(address_str, address_type, network_id)
    _validate_address_network_id(address_bytes, network_id)


def _validate_address_size(address_bytes: bytes) -> None:
    if not (MIN_ADDRESS_BYTES_LENGTH <= len(address_bytes) <= MAX_ADDRESS_BYTES_LENGTH):
        raise INVALID_ADDRESS


def _validate_address_bech32_hrp(
    address_str: str, address_type: CardanoAddressType, network_id: int
) -> None:
    valid_hrp = _get_bech32_hrp_for_address(address_type, network_id)
    bech32_hrp = bech32.get_hrp(address_str)

    if valid_hrp != bech32_hrp:
        raise INVALID_ADDRESS


def _get_bech32_hrp_for_address(
    address_type: CardanoAddressType, network_id: int
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


def get_public_key_hash(keychain: seed.Keychain, path: list[int]) -> bytes:
    public_key = derive_public_key(keychain, path)
    return hashlib.blake2b(data=public_key, outlen=ADDRESS_KEY_HASH_SIZE).digest()


def derive_human_readable_address(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> str:
    address_bytes = derive_address_bytes(
        keychain, parameters, protocol_magic, network_id
    )

    return encode_human_readable_address(address_bytes)


def encode_human_readable_address(address_bytes: bytes) -> str:
    address_type = _get_address_type(address_bytes)
    if address_type == CardanoAddressType.BYRON:
        return base58.encode(address_bytes)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        hrp = _get_bech32_hrp_for_address(
            address_type, _get_address_network_id(address_bytes)
        )
        return bech32.encode(hrp, address_bytes)
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
        address = derive_byron_address(keychain, parameters.address_n, protocol_magic)
    else:
        address = _derive_shelley_address(keychain, parameters, network_id)

    return address


def _derive_shelley_address(
    keychain: seed.Keychain,
    parameters: CardanoAddressParametersType,
    network_id: int,
) -> bytes:
    if parameters.address_type == CardanoAddressType.BASE:
        address = _derive_base_address(
            keychain,
            parameters.address_n,
            parameters.address_n_staking,
            parameters.staking_key_hash,
            network_id,
        )
    elif parameters.address_type == CardanoAddressType.POINTER:
        # ensured by validate_address_parameters
        assert parameters.certificate_pointer is not None

        address = _derive_pointer_address(
            keychain,
            parameters.address_n,
            parameters.certificate_pointer,
            network_id,
        )
    elif parameters.address_type == CardanoAddressType.ENTERPRISE:
        address = _derive_enterprise_address(keychain, parameters.address_n, network_id)
    elif parameters.address_type == CardanoAddressType.REWARD:
        address = _derive_reward_address(keychain, parameters.address_n, network_id)
    else:
        raise INVALID_ADDRESS_PARAMETERS

    return address


def _create_address_header(address_type: CardanoAddressType, network_id: int) -> bytes:
    header: int = address_type << 4 | network_id
    return header.to_bytes(1, "little")


def _derive_base_address(
    keychain: seed.Keychain,
    path: list[int],
    staking_path: list[int],
    staking_key_hash: bytes | None,
    network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.BASE, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)

    if staking_key_hash is None:
        staking_key_hash = get_public_key_hash(keychain, staking_path)

    return header + spending_key_hash + staking_key_hash


def _derive_pointer_address(
    keychain: seed.Keychain,
    path: list[int],
    pointer: CardanoBlockchainPointerType,
    network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.POINTER, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)
    encoded_pointer = _encode_certificate_pointer(pointer)

    return header + spending_key_hash + encoded_pointer


def _encode_certificate_pointer(pointer: CardanoBlockchainPointerType) -> bytes:
    block_index_encoded = variable_length_encode(pointer.block_index)
    tx_index_encoded = variable_length_encode(pointer.tx_index)
    certificate_index_encoded = variable_length_encode(pointer.certificate_index)

    return bytes(block_index_encoded + tx_index_encoded + certificate_index_encoded)


def _derive_enterprise_address(
    keychain: seed.Keychain,
    path: list[int],
    network_id: int,
) -> bytes:
    header = _create_address_header(CardanoAddressType.ENTERPRISE, network_id)
    spending_key_hash = get_public_key_hash(keychain, path)

    return header + spending_key_hash


def _derive_reward_address(
    keychain: seed.Keychain,
    path: list[int],
    network_id: int,
) -> bytes:
    staking_key_hash = get_public_key_hash(keychain, path)

    return pack_reward_address_bytes(staking_key_hash, network_id)


def pack_reward_address_bytes(
    staking_key_hash: bytes,
    network_id: int,
) -> bytes:
    """
    Helper function to transform raw staking key hash into reward address
    """
    header = _create_address_header(CardanoAddressType.REWARD, network_id)

    return header + staking_key_hash
