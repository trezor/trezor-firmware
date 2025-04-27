from typing import TYPE_CHECKING

from trezor.strings import format_amount, format_timestamp

if TYPE_CHECKING:
    from .definitions import Definitions


def format_pubkey(value: bytes | None) -> str:
    from trezor.crypto import base58

    if value is None:
        raise ValueError  # should not be called with optional pubkey

    return base58.encode(value)


def format_lamports(value: int) -> str:
    formatted = format_amount(value, decimals=9)
    return f"{formatted} SOL"


def format_token_amount(
    value: int, definitions: Definitions, decimals: int, mint: bytes
) -> str:
    formatted = format_amount(value, decimals=decimals)
    token = definitions.get_token(mint)
    return f"{formatted} {token.symbol}"


def format_unix_timestamp(value: int) -> str:
    return format_timestamp(value)


def format_int(value: int) -> str:
    return str(value)


def format_identity(value: str) -> str:
    return value
