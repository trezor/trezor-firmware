from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple

from . import exceptions, messages
from .tools import b58decode, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address

def get_address(
    client: "TrezorClient", n: "Address", prefix: str, show_display: bool = False
) -> messages.CosmosAddress:
    return client.call(
        messages.CosmosGetAddress(address_n=n, prefix=prefix, show_display=show_display),
        expect=messages.CosmosAddress,
    )

def get_public_key(
    client: "TrezorClient", n: "Address", show_display: bool = False
) -> messages.CosmosPublicKey:
    return client.call(
        messages.CosmosGetPublicKey(address_n=n, show_display=show_display),
        expect=messages.CosmosPublicKey,
    )

def sign_tx(
    client: "TrezorClient", n: "Address", sign_doc: bytes
) -> messages.CosmosSignedTx:
    return client.call(
        messages.CosmosSignTx(address_n=n, sign_doc=sign_doc),
        expect=messages.CosmosSignedTx,
    )