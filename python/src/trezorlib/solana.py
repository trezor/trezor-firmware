from typing import TYPE_CHECKING, List

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


@expect(messages.SolanaPublicKey)
def get_public_key(
    client: "TrezorClient",
    address_n: List[int],
) -> "MessageType":
    return client.call(messages.SolanaGetPublicKey(address_n=address_n))


@expect(messages.SolanaAddress)
def get_address(
    client: "TrezorClient",
    address_n: List[int],
    show_display: bool,
) -> "MessageType":
    return client.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
        )
    )


@expect(messages.SolanaSignedTx)
def sign_tx(
    client: "TrezorClient",
    signer_path_n: List[int],
    serialized_tx: bytes,
) -> "MessageType":
    return client.call(
        messages.SolanaSignTx(
            signer_path_n=signer_path_n,
            serialized_tx=serialized_tx,
        )
    )
