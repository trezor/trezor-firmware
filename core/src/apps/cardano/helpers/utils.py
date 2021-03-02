from trezor.crypto import hashlib

from apps.cardano.helpers.paths import ACCOUNT_PATH_INDEX, unharden

from . import bech32

if False:
    from typing import List, Optional


def variable_length_encode(number: int) -> bytes:
    """
    Used for pointer encoding in pointer address.
    Encoding description can be found here:
    https://en.wikipedia.org/wiki/Variable-length_quantity
    """
    if number < 0:
        raise ValueError("Negative numbers not supported. Number supplied: %s" % number)

    encoded = []

    bit_length = len(bin(number)[2:])
    encoded.append(number & 127)

    while bit_length > 7:
        number >>= 7
        bit_length -= 7
        encoded.insert(0, (number & 127) + 128)

    return bytes(encoded)


def to_account_path(path: List[int]) -> List[int]:
    return path[: ACCOUNT_PATH_INDEX + 1]


def format_account_number(path: List[int]) -> str:
    if len(path) <= ACCOUNT_PATH_INDEX:
        raise ValueError("Path is too short.")

    return "#%d" % (unharden(path[ACCOUNT_PATH_INDEX]) + 1)


def format_optional_int(number: Optional[int]) -> str:
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
