from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
    value: Optional[bytes],
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
) -> tuple[bool, bool, int]:
    """Verify an MPT proof against the stored root.

    For a membership proof supply value; leave witness_address/witness_value None.
    For a non-membership proof supply witness_address and witness_value; value may be None.

    Returns (valid, membership, counter).
    """
    resp = session.call(
        messages.AuthDbLookup(
            address=address,
            value=value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter


def update_leaf(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
) -> tuple[int, Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).

    Returns (counter, new_root).  new_root is None if the tree is now empty.
    """
    resp = session.call(
        messages.AuthDbUpdateLeaf(
            address=address,
            old_value=old_value,
            new_value=new_value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
        ),
        expect=messages.AuthDbUpdateLeafResponse,
    )
    return resp.counter, resp.new_root
