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
    address: bytes,
    value: bytes,
    proof: list[bytes],
) -> tuple[bool, int]:
    """Verify a Sparse Merkle Tree proof for (address, value) against stored root.

    proof must be in leaf-to-root order, as returned by AuthDbTree.get_proof().
    Returns (valid, counter).
    """
    resp = session.call(
        messages.AuthDbLookup(
            address=address,
            value=value,
            proof=proof,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    return resp.valid, resp.counter
