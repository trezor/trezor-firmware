from typing import TYPE_CHECKING

from trezor.crypto import base58

if TYPE_CHECKING:

    from buffer_types import AnyBytes


def get_encoded_address(address_bytes: AnyBytes) -> str:
    """Encodes raw address bytes into Tron format."""
    address = base58.encode_check(address_bytes)
    if len(address) != 34 or address[0] != "T":
        raise ValueError("Tron: Invalid address")
    return address
