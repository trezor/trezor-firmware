from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.enums import CardanoAddressType
from trezor.wire import ProcessError

from . import byron_addresses
from .helpers import bech32
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .helpers.utils import get_public_key_hash

if TYPE_CHECKING:
    from typing import Any

    from trezor import messages

    from .seed import Keychain


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

ADDRESS_TYPES_PAYMENT_KEY = (
    CardanoAddressType.BASE,
    CardanoAddressType.BASE_KEY_SCRIPT,
    CardanoAddressType.POINTER,
    CardanoAddressType.ENTERPRISE,
    CardanoAddressType.BYRON,
)

ADDRESS_TYPES_PAYMENT_SCRIPT = (
    CardanoAddressType.BASE_SCRIPT_KEY,
    CardanoAddressType.BASE_SCRIPT_SCRIPT,
    CardanoAddressType.POINTER_SCRIPT,
    CardanoAddressType.ENTERPRISE_SCRIPT,
)

ADDRESS_TYPES_PAYMENT = ADDRESS_TYPES_PAYMENT_KEY + ADDRESS_TYPES_PAYMENT_SCRIPT

_MIN_ADDRESS_BYTES_LENGTH = const(29)
_MAX_ADDRESS_BYTES_LENGTH = const(65)


def assert_params_cond(condition: bool) -> None:
    if not condition:
        raise ProcessError("Invalid address parameters")


def validate_address_parameters(
    parameters: messages.CardanoAddressParametersType,
) -> None:
    from . import seed

    _validate_address_parameters_structure(parameters)
    address_type = parameters.address_type  # local_cache_attribute
    address_n = parameters.address_n  # local_cache_attribute
    address_n_staking = parameters.address_n_staking  # local_cache_attribute
    script_payment_hash = parameters.script_payment_hash  # local_cache_attribute
    is_shelley_path = seed.is_shelley_path  # local_cache_attribute
    CAT = CardanoAddressType  # local_cache_global

    if address_type == CAT.BYRON:
        assert_params_cond(seed.is_byron_path(address_n))

    elif address_type == CAT.BASE:
        assert_params_cond(is_shelley_path(address_n))
        _validate_base_address_staking_info(
            address_n_staking, parameters.staking_key_hash
        )

    elif address_type == CAT.BASE_SCRIPT_KEY:
        _validate_script_hash(script_payment_hash)
        _validate_base_address_staking_info(
            address_n_staking, parameters.staking_key_hash
        )

    elif address_type == CAT.BASE_KEY_SCRIPT:
        assert_params_cond(is_shelley_path(address_n))
        _validate_script_hash(parameters.script_staking_hash)

    elif address_type == CAT.BASE_SCRIPT_SCRIPT:
        _validate_script_hash(script_payment_hash)
        _validate_script_hash(parameters.script_staking_hash)

    elif address_type == CAT.POINTER:
        assert_params_cond(is_shelley_path(address_n))
        assert_params_cond(parameters.certificate_pointer is not None)

    elif address_type == CAT.POINTER_SCRIPT:
        _validate_script_hash(script_payment_hash)
        assert_params_cond(parameters.certificate_pointer is not None)

    elif address_type == CAT.ENTERPRISE:
        assert_params_cond(is_shelley_path(address_n))

    elif address_type == CAT.ENTERPRISE_SCRIPT:
        _validate_script_hash(script_payment_hash)

    elif address_type == CAT.REWARD:
        assert_params_cond(is_shelley_path(address_n_staking))
        assert_params_cond(SCHEMA_STAKING_ANY_ACCOUNT.match(address_n_staking))

    elif address_type == CAT.REWARD_SCRIPT:
        _validate_script_hash(parameters.script_staking_hash)

    else:
        raise RuntimeError  # should be unreachable


def _validate_address_parameters_structure(
    parameters: messages.CardanoAddressParametersType,
) -> None:
    address_n = parameters.address_n  # local_cache_attribute
    address_n_staking = parameters.address_n_staking  # local_cache_attribute
    staking_key_hash = parameters.staking_key_hash  # local_cache_attribute
    certificate_pointer = parameters.certificate_pointer  # local_cache_attribute
    script_payment_hash = parameters.script_payment_hash  # local_cache_attribute
    script_staking_hash = parameters.script_staking_hash  # local_cache_attribute
    CAT = CardanoAddressType  # local_cache_global

    fields_to_be_empty: dict[CAT, tuple[Any, ...]] = {
        CAT.BASE: (
            certificate_pointer,
            script_payment_hash,
            script_staking_hash,
        ),
        CAT.BASE_KEY_SCRIPT: (
            address_n_staking,
            certificate_pointer,
            script_payment_hash,
        ),
        CAT.BASE_SCRIPT_KEY: (
            address_n,
            certificate_pointer,
            script_staking_hash,
        ),
        CAT.BASE_SCRIPT_SCRIPT: (
            address_n,
            address_n_staking,
            certificate_pointer,
        ),
        CAT.POINTER: (
            address_n_staking,
            staking_key_hash,
            script_payment_hash,
            script_staking_hash,
        ),
        CAT.POINTER_SCRIPT: (
            address_n,
            address_n_staking,
            staking_key_hash,
            script_staking_hash,
        ),
        CAT.ENTERPRISE: (
            address_n_staking,
            staking_key_hash,
            certificate_pointer,
            script_payment_hash,
            script_staking_hash,
        ),
        CAT.ENTERPRISE_SCRIPT: (
            address_n,
            address_n_staking,
            staking_key_hash,
            certificate_pointer,
            script_staking_hash,
        ),
        CAT.BYRON: (
            address_n_staking,
            staking_key_hash,
            certificate_pointer,
            script_payment_hash,
            script_staking_hash,
        ),
        CAT.REWARD: (
            address_n,
            staking_key_hash,
            certificate_pointer,
            script_payment_hash,
            script_staking_hash,
        ),
        CAT.REWARD_SCRIPT: (
            address_n,
            address_n_staking,
            staking_key_hash,
            certificate_pointer,
            script_payment_hash,
        ),
    }

    assert_params_cond(parameters.address_type in fields_to_be_empty)
    assert_params_cond(not any(fields_to_be_empty[parameters.address_type]))


def _validate_base_address_staking_info(
    staking_path: list[int],
    staking_key_hash: bytes | None,
) -> None:
    from .helpers import ADDRESS_KEY_HASH_SIZE

    assert_params_cond(not (staking_key_hash and staking_path))

    if staking_key_hash:
        assert_params_cond(len(staking_key_hash) == ADDRESS_KEY_HASH_SIZE)
    elif staking_path:
        assert_params_cond(SCHEMA_STAKING_ANY_ACCOUNT.match(staking_path))
    else:
        raise ProcessError("Invalid address parameters")


def _validate_script_hash(script_hash: bytes | None) -> None:
    from .helpers import SCRIPT_HASH_SIZE

    assert_params_cond(script_hash is not None and len(script_hash) == SCRIPT_HASH_SIZE)


def validate_output_address_parameters(
    parameters: messages.CardanoAddressParametersType,
) -> None:
    validate_address_parameters(parameters)

    # Change outputs with script payment part are forbidden.
    # Reward addresses are forbidden as outputs in general, see also validate_output_address
    assert_params_cond(parameters.address_type in ADDRESS_TYPES_PAYMENT_KEY)


def validate_cvote_payment_address_parameters(
    parameters: messages.CardanoAddressParametersType,
) -> None:
    validate_address_parameters(parameters)
    assert_params_cond(parameters.address_type in ADDRESS_TYPES_SHELLEY)


def assert_cond(condition: bool) -> None:
    if not condition:
        raise ProcessError("Invalid address")


def _validate_and_get_type(address: str, protocol_magic: int, network_id: int) -> int:
    """
    Validates Cardano address and returns its type
    for the convenience of outward-facing functions.
    """
    assert_cond(address is not None)
    assert_cond(len(address) > 0)

    address_bytes = get_bytes_unsafe(address)
    address_type = get_type(address_bytes)

    if address_type == CardanoAddressType.BYRON:
        byron_addresses.validate(address_bytes, protocol_magic)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        # _validate_shelley_address

        # _validate_size
        assert_cond(
            _MIN_ADDRESS_BYTES_LENGTH <= len(address_bytes) <= _MAX_ADDRESS_BYTES_LENGTH
        )

        # _validate_bech32_hrp
        valid_hrp = _get_bech32_hrp(address_type, network_id)
        # get_hrp
        bech32_hrp = address.rsplit(bech32.HRP_SEPARATOR, 1)[0]
        assert_cond(valid_hrp == bech32_hrp)

        # _validate_network_id
        if _get_network_id(address_bytes) != network_id:
            raise ProcessError("Output address network mismatch")
    else:
        raise ProcessError("Invalid address")

    return address_type


def validate_output_address(address: str, protocol_magic: int, network_id: int) -> None:
    address_type = _validate_and_get_type(address, protocol_magic, network_id)
    assert_cond(
        address_type
        not in (CardanoAddressType.REWARD, CardanoAddressType.REWARD_SCRIPT)
    )


def validate_reward_address(address: str, protocol_magic: int, network_id: int) -> None:
    address_type = _validate_and_get_type(address, protocol_magic, network_id)
    assert_cond(
        address_type in (CardanoAddressType.REWARD, CardanoAddressType.REWARD_SCRIPT)
    )


def validate_cvote_payment_address(
    address: str, protocol_magic: int, network_id: int
) -> None:
    address_type = _validate_and_get_type(address, protocol_magic, network_id)
    assert_cond(address_type in ADDRESS_TYPES_SHELLEY)


def get_bytes_unsafe(address: str) -> bytes:
    try:
        address_bytes = bech32.decode_unsafe(address)
    except ValueError:
        try:
            address_bytes = base58.decode(address)
        except ValueError:
            raise ProcessError("Invalid address")

    return address_bytes


def get_type(address: bytes) -> CardanoAddressType:
    return address[0] >> 4  # type: ignore [int-into-enum]


def _get_bech32_hrp(address_type: CardanoAddressType, network_id: int) -> str:
    from .helpers import bech32, network_ids

    if address_type == CardanoAddressType.BYRON:
        # Byron address uses base58 encoding
        raise ValueError

    if address_type in (CardanoAddressType.REWARD, CardanoAddressType.REWARD_SCRIPT):
        if network_ids.is_mainnet(network_id):
            return bech32.HRP_REWARD_ADDRESS
        else:
            return bech32.HRP_TESTNET_REWARD_ADDRESS
    else:
        if network_ids.is_mainnet(network_id):
            return bech32.HRP_ADDRESS
        else:
            return bech32.HRP_TESTNET_ADDRESS


def _get_network_id(address: bytes) -> int:
    return address[0] & 0x0F


def derive_human_readable(
    keychain: Keychain,
    parameters: messages.CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> str:
    address_bytes = derive_bytes(keychain, parameters, protocol_magic, network_id)
    return encode_human_readable(address_bytes)


def encode_human_readable(address_bytes: bytes) -> str:
    address_type = get_type(address_bytes)
    if address_type == CardanoAddressType.BYRON:
        return base58.encode(address_bytes)
    elif address_type in ADDRESS_TYPES_SHELLEY:
        hrp = _get_bech32_hrp(address_type, _get_network_id(address_bytes))
        return bech32.encode(hrp, address_bytes)
    else:
        raise ValueError


def derive_bytes(
    keychain: Keychain,
    parameters: messages.CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
) -> bytes:
    is_byron_address = parameters.address_type == CardanoAddressType.BYRON

    if is_byron_address:
        address = byron_addresses.derive(keychain, parameters.address_n, protocol_magic)
    else:
        address = _derive_shelley_address(keychain, parameters, network_id)

    return address


def _derive_shelley_address(
    keychain: Keychain,
    parameters: messages.CardanoAddressParametersType,
    network_id: int,
) -> bytes:
    # _create_header
    header_int = parameters.address_type << 4 | network_id
    header = header_int.to_bytes(1, "little")

    payment_part = _get_payment_part(keychain, parameters)
    staking_part = _get_staking_part(keychain, parameters)

    return header + payment_part + staking_part


def _get_payment_part(
    keychain: Keychain, parameters: messages.CardanoAddressParametersType
) -> bytes:
    if parameters.address_n:
        return get_public_key_hash(keychain, parameters.address_n)
    elif parameters.script_payment_hash:
        return parameters.script_payment_hash
    else:
        return bytes()


def _get_staking_part(
    keychain: Keychain, parameters: messages.CardanoAddressParametersType
) -> bytes:
    from .helpers.utils import variable_length_encode

    if parameters.staking_key_hash:
        return parameters.staking_key_hash
    elif parameters.address_n_staking:
        return get_public_key_hash(keychain, parameters.address_n_staking)
    elif parameters.script_staking_hash:
        return parameters.script_staking_hash
    elif parameters.certificate_pointer:
        # _encode_certificate_pointer
        pointer = parameters.certificate_pointer
        block_index_encoded = variable_length_encode(pointer.block_index)
        tx_index_encoded = variable_length_encode(pointer.tx_index)
        certificate_index_encoded = variable_length_encode(pointer.certificate_index)
        return bytes(block_index_encoded + tx_index_encoded + certificate_index_encoded)
    else:
        return bytes()
