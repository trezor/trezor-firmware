"""CKB (Nervos Network) support for Trezor."""

from typing import TYPE_CHECKING, Any

from . import messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session

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
