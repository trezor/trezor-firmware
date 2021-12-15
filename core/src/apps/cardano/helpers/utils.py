from trezor.crypto import hashlib
from trezor.enums import CardanoTxSigningMode

from apps.cardano.helpers.paths import (
    ACCOUNT_PATH_INDEX,
    SCHEMA_STAKING_ANY_ACCOUNT,
    unharden,
)
from apps.common.seed import remove_ed25519_prefix

from . import ADDRESS_KEY_HASH_SIZE, SCRIPT_HASH_SIZE, bech32

if False:
    from trezor import wire
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


def format_script_hash(script_hash: bytes) -> str:
    return bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash)


def format_key_hash(key_hash: bytes, is_shared_key: bool) -> str:
    hrp = bech32.HRP_SHARED_KEY_HASH if is_shared_key else bech32.HRP_KEY_HASH
    return bech32.encode(hrp, key_hash)


def get_public_key_hash(keychain: seed.Keychain, path: list[int]) -> bytes:
    public_key = derive_public_key(keychain, path)
    return hashlib.blake2b(data=public_key, outlen=ADDRESS_KEY_HASH_SIZE).digest()


def derive_public_key(
    keychain: seed.Keychain, path: list[int], extended: bool = False
) -> bytes:
    node = keychain.derive(path)
    public_key = remove_ed25519_prefix(node.public_key())
    return public_key if not extended else public_key + node.chain_code()


def validate_stake_credential(
    path: list[int],
    script_hash: bytes | None,
    signing_mode: CardanoTxSigningMode,
    error: wire.ProcessError,
) -> None:
    if path and script_hash:
        raise error

    if path:
        if signing_mode != CardanoTxSigningMode.ORDINARY_TRANSACTION:
            raise error
        if not SCHEMA_STAKING_ANY_ACCOUNT.match(path):
            raise error
    elif script_hash:
        if signing_mode != CardanoTxSigningMode.MULTISIG_TRANSACTION:
            raise error
        if len(script_hash) != SCRIPT_HASH_SIZE:
            raise error
    else:
        raise error
