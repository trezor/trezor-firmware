from typing import TYPE_CHECKING, Any

from . import messages

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address

DEFAULT_BIP32_PATH = "m/44h/195h/0h/0/0"


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.TronAddress:
    return client.call(
        messages.TronGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TronAddress,
    )
