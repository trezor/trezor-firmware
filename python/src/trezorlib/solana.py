from typing import TYPE_CHECKING, List, Optional

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .protobuf import MessageType
    from .transport.session import Session


@expect(messages.SolanaPublicKey)
def get_public_key(
    session: "Session",
    address_n: List[int],
    show_display: bool,
) -> "MessageType":
    return session.call(
        messages.SolanaGetPublicKey(address_n=address_n, show_display=show_display)
    )


@expect(messages.SolanaAddress)
def get_address(
    session: "Session",
    address_n: List[int],
    show_display: bool,
    chunkify: bool = False,
) -> "MessageType":
    return session.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
            chunkify=chunkify,
        )
    )


@expect(messages.SolanaTxSignature)
def sign_tx(
    session: "Session",
    address_n: List[int],
    serialized_tx: bytes,
    additional_info: Optional[messages.SolanaTxAdditionalInfo],
) -> "MessageType":
    return session.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
            additional_info=additional_info,
        )
    )
