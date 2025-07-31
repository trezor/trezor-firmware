from typing import TYPE_CHECKING, Any, List, Optional

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def get_public_key(
    session: "Session",
    address_n: List[int],
    show_display: bool,
) -> bytes:
    return session.call(
        messages.SolanaGetPublicKey(address_n=address_n, show_display=show_display),
        expect=messages.SolanaPublicKey,
    ).public_key


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    address_n: List[int],
    show_display: bool,
    chunkify: bool = False,
) -> messages.SolanaAddress:
    return session.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
            chunkify=chunkify,
        ),
        expect=messages.SolanaAddress,
    )


def sign_tx(
    session: "Session",
    address_n: List[int],
    serialized_tx: bytes,
    additional_info: Optional[messages.SolanaTxAdditionalInfo],
) -> bytes:
    return session.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
            additional_info=additional_info,
        ),
        expect=messages.SolanaTxSignature,
    ).signature
