"""CKB (Nervos Network) support for Trezor."""

from typing import TYPE_CHECKING, Any

from . import messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session


# CKB uses secp256k1 curve (coin_type 309 per SLIP-44)
CURVE = "secp256k1"
SLIP44_ID = 309
DEFAULT_BIP32_PATH = "m/44h/309h/0h/0/0"


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    network: str = "Mainnet",
    chunkify: bool = False,
) -> messages.CKBAddress:
    return session.call(
        messages.CKBGetAddress(
            address_n=address_n,
            show_display=show_display,
            network=network,
            chunkify=chunkify,
        ),
        expect=messages.CKBAddress,
    )
