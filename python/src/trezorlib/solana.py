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


@expect(messages.SolanaTxSignature)
def sign_tx(
    client: "TrezorClient",
    address_n: List[int],
    serialized_tx: bytes,
) -> "MessageType":
    return client.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
        )
    )


@expect(messages.SolanaOffChainMessageSignature)
def sign_off_chain_message(
    client: "TrezorClient",
    address_n: List[int],
    serialized_message: bytes,
) -> "MessageType":
    return client.call(
        messages.SolanaSignOffChainMessage(
            address_n=address_n,
            serialized_message=serialized_message,
        )
    )
