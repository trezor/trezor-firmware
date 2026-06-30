from __future__ import annotations

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def set_root(session: "Session", root: bytes) -> int:
    """Store a new Merkle root on the device and return the updated counter."""
    resp = session.call(
        messages.AuthDbSetRoot(root=root),
        expect=messages.AuthDbSetRootResponse,
    )
    return resp.counter


def lookup(
    session: "Session",
    leaf_hash: bytes,
    proof: list[bytes],
) -> tuple[bool, int]:
    """Verify a Merkle proof against the stored root.

    leaf_hash must be SHA-256(b"\\x00" + raw_value) as per trezorlib.merkle_tree.
    Returns (valid, counter).
    """
    resp = session.call(
        messages.AuthDbLookup(
            leaf_hash=leaf_hash,
            proof=proof,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    return resp.valid, resp.counter
