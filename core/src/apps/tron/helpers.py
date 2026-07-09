from typing import TYPE_CHECKING

from trezor.crypto import base58

if TYPE_CHECKING:

    from buffer_types import AnyBytes


def address_from_public_key(pubkey: bytes) -> str:
    from trezor.crypto.hashlib import sha3_256

    address_bytes = b"\x41" + sha3_256(pubkey[1:], keccak=True).digest()[12:]
    return base58.encode_check(address_bytes)


def get_encoded_address(address_bytes: AnyBytes) -> str:
    """Encodes raw address bytes into Tron format."""
    address = base58.encode_check(address_bytes)
    if len(address) != 34 or address[0] != "T":
        raise ValueError("Tron: Invalid address")
    return address
