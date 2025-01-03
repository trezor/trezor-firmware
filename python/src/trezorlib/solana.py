from typing import TYPE_CHECKING, List, Optional

from . import messages

if TYPE_CHECKING:
    from .client import TrezorClient


def get_public_key(
    client: "TrezorClient",
    address_n: List[int],
    show_display: bool,
) -> bytes:
    return client.call(
        messages.SolanaGetPublicKey(address_n=address_n, show_display=show_display),
        expect=messages.SolanaPublicKey,
    ).public_key


def get_address(
    client: "TrezorClient",
    address_n: List[int],
    show_display: bool,
    chunkify: bool = False,
) -> str:
    return client.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
            chunkify=chunkify,
        ),
        expect=messages.SolanaAddress,
    ).address


def sign_tx(
    client: "TrezorClient",
    address_n: List[int],
    serialized_tx: bytes,
    additional_info: Optional[messages.SolanaTxAdditionalInfo],
) -> bytes:
    return client.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
            additional_info=additional_info,
        ),
        expect=messages.SolanaTxSignature,
    ).signature
