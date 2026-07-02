from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def set_root(
    session: "Session",
    root: bytes,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes]]:
    """Store a new Merkle root on the device. DEBUG BUILDS ONLY.

    Returns (counter, identifier).
    """
    resp = session.call(
        messages.AuthDbSetRoot(root=root, mac=mac, device_id=device_id),
        expect=messages.AuthDbSetRootResponse,
    )
    return resp.counter, resp.identifier


def lookup(
    session: "Session",
    address: bytes,
    value: Optional[bytes],
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify an MPT proof against the stored root.

    For a membership proof supply value; leave witness_address/witness_value None.
    For a non-membership proof supply witness_address and witness_value; value may be None.

    Returns (valid, membership, counter, identifier).
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
    return resp.valid, membership, resp.counter, resp.identifier


def clear_root(session: "Session") -> Optional[bytes]:
    """Wipe the stored Merkle root. DEBUG BUILDS ONLY.

    Returns identifier.
    """
    resp = session.call(
        messages.AuthDbClearRoot(),
        expect=messages.AuthDbClearRootResponse,
    )
    return resp.identifier


def update_leaf(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).
    mac + device_id skip the on-screen confirmation if they match a prior approve() call.

    Returns (counter, new_root, identifier, mac).  new_root/mac are None if tree is now empty.
    """
    resp = session.call(
        messages.AuthDbUpdateLeaf(
            address=address,
            old_value=old_value,
            new_value=new_value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            mac=mac,
            device_id=device_id,
        ),
        expect=messages.AuthDbUpdateLeafResponse,
    )
    return resp.counter, resp.new_root, resp.identifier, resp.mac


def approve(
    session: "Session",
    address: bytes,
    value: bytes,
) -> tuple[bytes, Optional[bytes]]:
    """Pre-authorize an (address, value) pair on the device.

    The user confirms on-screen; the device returns a MAC token that can be
    passed to future update_leaf calls to skip the confirmation dialog.

    Returns (mac, identifier).
    """
    resp = session.call(
        messages.AuthDbApprove(address=address, value=value),
        expect=messages.AuthDbApproveResponse,
    )
    return resp.mac, resp.identifier
