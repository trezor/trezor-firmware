from typing import TYPE_CHECKING

from trezor.crypto import hashlib

from . import ADDRESS_KEY_HASH_SIZE, bech32
from .paths import ACCOUNT_PATH_INDEX

if TYPE_CHECKING:
    from trezor.wire import ProcessError

    from .. import seed


def variable_length_encode(number: int) -> bytes:
    """
    Used for pointer encoding in pointer address.
    Encoding description can be found here:
    https://en.wikipedia.org/wiki/Variable-length_quantity
    """
    if number < 0:
        raise ValueError(f"Negative numbers not supported. Number supplied: {number}")

    encoded = [number & 0x7F]
    while number > 0x7F:
        number >>= 7
        encoded.append((number & 0x7F) + 0x80)

    return bytes(reversed(encoded))


def to_account_path(path: list[int]) -> list[int]:
    return path[: ACCOUNT_PATH_INDEX + 1]


def format_account_number(path: list[int]) -> str:
    from .paths import unharden

    if len(path) <= ACCOUNT_PATH_INDEX:
        raise ValueError("Path is too short.")

    return f"#{unharden(path[ACCOUNT_PATH_INDEX]) + 1}"


def format_optional_int(number: int | None) -> str:
    if number is None:
        return "n/a"

    return str(number)


def format_stake_pool_id(pool_id_bytes: bytes) -> str:
    return bech32.encode("pool", pool_id_bytes)


def format_asset_fingerprint(policy_id: bytes, asset_name_bytes: bytes) -> str:
    fingerprint = hashlib.blake2b(
        # bytearrays are being promoted to bytes: https://github.com/python/mypy/issues/654
        # but bytearrays are not concatenable, this casting works around this limitation
        data=bytes(policy_id) + bytes(asset_name_bytes),
        outlen=20,
    ).digest()

    return bech32.encode("asset", fingerprint)


def get_public_key_hash(keychain: seed.Keychain, path: list[int]) -> bytes:
    public_key = derive_public_key(keychain, path)
    return hashlib.blake2b(data=public_key, outlen=ADDRESS_KEY_HASH_SIZE).digest()


def derive_public_key(
    keychain: seed.Keychain, path: list[int], extended: bool = False
) -> bytes:
    from apps.common.seed import remove_ed25519_prefix

    node = keychain.derive(path)
    public_key = remove_ed25519_prefix(node.public_key())
    return public_key if not extended else public_key + node.chain_code()


def validate_stake_credential(
    path: list[int],
    script_hash: bytes | None,
    key_hash: bytes | None,
    error: ProcessError,
) -> None:
    from . import SCRIPT_HASH_SIZE
    from .paths import SCHEMA_STAKING_ANY_ACCOUNT

    if sum(bool(k) for k in (path, script_hash, key_hash)) != 1:
        raise error

    if path and not SCHEMA_STAKING_ANY_ACCOUNT.match(path):
        raise error
    if script_hash and len(script_hash) != SCRIPT_HASH_SIZE:
        raise error
    if key_hash and len(key_hash) != ADDRESS_KEY_HASH_SIZE:
        raise error


def validate_network_info(network_id: int, protocol_magic: int) -> None:
    """
    We are only concerned about checking that both network_id and protocol_magic
    belong to the mainnet or that both belong to a testnet. We don't need to check for
    consistency between various testnets (at least for now).
    """
    from trezor import wire

    from . import network_ids, protocol_magics

    is_mainnet_network_id = network_ids.is_mainnet(network_id)
    is_mainnet_protocol_magic = protocol_magics.is_mainnet(protocol_magic)

    if is_mainnet_network_id != is_mainnet_protocol_magic:
        raise wire.ProcessError("Invalid network id/protocol magic combination!")
