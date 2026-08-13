from __future__ import annotations

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def show_address(
    session: "Session",
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
) -> str:
    """Display an address with a PULL-authenticated WARD label: the device requests
    the proof on demand (WARDProofRequest), answered by the registered
    ``ward_proof_callback``. Register a callback before calling."""
    session.call(
        messages.DisplayAddress(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
        ),
        expect=messages.Success,
    )
    return address


def show_address_with_proof(
    session: "Session",
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
    proof: list[bytes] | None = None,
    leaf=None,
    app_id: str | None = None,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> str:
    """Display an address with a PUSH-authenticated WARD label: the host attaches the
    proof up-front (membership: the leaf's two parts via `leaf`, a
    ward_crypto.LeafBlob; non-membership: witness_entry_key + witness_commit)."""
    from .ward import make_leaf_content, make_leaf_identity

    session.call(
        messages.DisplayAddressWithProof(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
            proof=proof or [],
            app_id=app_id,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
            content=make_leaf_content(leaf.content if leaf is not None else None),
            identity=(
                make_leaf_identity(leaf.key_type, leaf.identity)
                if leaf is not None
                else None
            ),
        ),
        expect=messages.Success,
    )
    return address
