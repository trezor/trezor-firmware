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
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).
    mac + device_id skip the on-screen confirmation if they match a prior approve() call.

    Returns (counter, new_root, identifier, mac, auth_mac).
    new_root/mac are None if tree is now empty.
    auth_mac is set in debug/auto-approve mode: HMAC(device_key, old_leafHash||new_leafHash).
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
    return resp.counter, resp.new_root, resp.identifier, resp.mac, resp.auth_mac


def set_cache_entry(
    session: "Session",
    address: bytes,
    label: Optional[str] = None,
    data_mac: Optional[bytes] = None,
) -> int:
    """Store label and/or data_mac for address in the device offline cache.

    Returns identifier_crc (low 4 bytes of device_id) for sanity-checking.
    """
    resp = session.call(
        messages.AuthDbSetCacheEntry(address=address, label=label, data_mac=data_mac),
        expect=messages.AuthDbSetCacheEntryResponse,
    )
    return resp.identifier_crc


def get_cache_entry(
    session: "Session",
    address: bytes,
) -> tuple[bool, Optional[str], Optional[bytes]]:
    """Retrieve cached metadata for address.

    Returns (found, label, data_mac).
    """
    resp = session.call(
        messages.AuthDbGetCacheEntry(address=address),
        expect=messages.AuthDbGetCacheEntryResponse,
    )
    return resp.found, resp.label, resp.data_mac


def get_all_cache(
    session: "Session",
) -> list[tuple[bytes, Optional[str], Optional[bytes]]]:
    """Return all cached entries as (address, label, data_mac) tuples."""
    resp = session.call(
        messages.AuthDbGetAllCache(),
        expect=messages.AuthDbGetAllCacheResponse,
    )
    return [(e.address, e.label, e.data_mac) for e in resp.entries]


def wipe_cache(session: "Session") -> None:
    """Wipe all offline-cache entries from the device."""
    session.call(messages.AuthDbWipeCache(), expect=messages.AuthDbWipeCacheResponse)


def set_device_id(
    session: "Session",
    device_id: bytes,
) -> bytes:
    """Override the device_id on the device. DEBUG BUILDS ONLY.

    Returns the echoed device_id.
    """
    resp = session.call(
        messages.AuthDbSetDeviceId(device_id=device_id),
        expect=messages.AuthDbSetDeviceIdResponse,
    )
    return resp.device_id


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


# ---------------------------------------------------------------------------
# Offline synchronization
# ---------------------------------------------------------------------------

def queue_offline_operation(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> tuple[int, bytes, Optional[bytes]]:
    """Create a signed offline operation when the host database is unreachable.

    old_value=b"" means the address is currently absent (INSERT).
    new_value=b"" means delete the address (DELETE).

    Returns (sequence, mac, identifier). Does not touch the Merkle root.
    """
    resp = session.call(
        messages.AuthDbQueueOfflineOperation(
            address=address, old_value=old_value, new_value=new_value
        ),
        expect=messages.AuthDbQueueOfflineOperationResponse,
    )
    return resp.sequence, resp.mac, resp.identifier


class OfflineOperation:
    """One entry of the on-device offline queue, as returned by get_offline_operations()."""

    def __init__(
        self,
        sequence: int,
        address: bytes,
        old_value: bytes,
        new_value: bytes,
        mac: bytes,
    ) -> None:
        self.sequence = sequence
        self.address = address
        self.old_value = old_value
        self.new_value = new_value
        self.mac = mac


def get_offline_operations(
    session: "Session",
) -> tuple[Optional[bytes], int, Optional[bytes], list[OfflineOperation]]:
    """Fetch the current root/counter plus every queued offline operation, for upload.

    Returns (current_root, counter, identifier, operations).
    """
    resp = session.call(
        messages.AuthDbGetOfflineOperations(),
        expect=messages.AuthDbGetOfflineOperationsResponse,
    )
    operations = [
        OfflineOperation(
            sequence=op.sequence,
            address=op.address,
            old_value=op.old_value if op.old_value else b"",
            new_value=op.new_value if op.new_value else b"",
            mac=op.mac,
        )
        for op in resp.operations
    ]
    return resp.current_root, resp.counter, resp.identifier, operations


class RebasedOperation:
    """One operation, rebased by the host against the current canonical root.

    sequence/address/old_value/new_value/mac must be forwarded byte-for-byte
    from the OfflineOperation it originates from -- rebase may choose whether
    to forward an operation, never alter its signed fields.
    """

    def __init__(
        self,
        sequence: int,
        address: bytes,
        old_value: bytes,
        new_value: bytes,
        mac: bytes,
        proof: list[bytes],
        witness_address: Optional[bytes] = None,
        witness_value: Optional[bytes] = None,
    ) -> None:
        self.sequence = sequence
        self.address = address
        self.old_value = old_value
        self.new_value = new_value
        self.mac = mac
        self.proof = proof
        self.witness_address = witness_address
        self.witness_value = witness_value


def apply_offline_operations(
    session: "Session",
    operations: list[RebasedOperation],
) -> tuple[int, Optional[bytes], int, int, Optional[bytes]]:
    """Apply a batch of host-rebased offline operations.

    The device independently verifies each operation's MAC and Merkle proof
    and computes the resulting root itself; it never accepts a host-supplied
    root. Processing stops at the first operation that fails verification or
    is not the immediate next expected sequence.

    Returns (applied_count, new_root, counter, last_applied_sequence, identifier).
    """
    resp = session.call(
        messages.AuthDbApplyOfflineOperations(
            operations=[
                messages.AuthDbRebasedOperation(
                    sequence=op.sequence,
                    address=op.address,
                    old_value=op.old_value,
                    new_value=op.new_value,
                    mac=op.mac,
                    proof=op.proof,
                    witness_address=op.witness_address,
                    witness_value=op.witness_value,
                )
                for op in operations
            ]
        ),
        expect=messages.AuthDbApplyOfflineOperationsResponse,
    )
    return (
        resp.applied_count,
        resp.new_root,
        resp.counter,
        resp.last_applied_sequence,
        resp.identifier,
    )


def delete_offline_operations(session: "Session") -> tuple[int, int]:
    """Delete every queued operation with sequence <= the device's own last_applied_sequence.

    Takes no input: the device is the sole source of truth for what it has
    actually applied, so garbage collection cannot be tricked into deleting
    an operation that was never really committed.

    Returns (deleted_count, remaining_count).
    """
    resp = session.call(
        messages.AuthDbDeleteOfflineOperations(),
        expect=messages.AuthDbDeleteOfflineOperationsResponse,
    )
    return resp.deleted_count, resp.remaining_count
