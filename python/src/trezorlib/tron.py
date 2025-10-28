from typing import TYPE_CHECKING, Any

from . import messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session

DEFAULT_BIP32_PATH = "m/44h/195h/0h/0/0"


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.TronAddress:
    return session.call(
        messages.TronGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TronAddress,
    )
