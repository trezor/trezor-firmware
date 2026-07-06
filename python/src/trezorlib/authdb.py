from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


ZERO_MAC = b"\x00" * 32


def set_root(
    session: "Session",
    root: bytes,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
    counter: Optional[int] = None,
    operations: Optional[list["RebasedOperation"]] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], int, int, Optional[bytes]]:
    """Install a (root, counter) state and replay `operations` (this wallet's
    own pending queue, if any) on top of it, in one call.

    mac defaults to the all-zero sentinel -- a plain unauthenticated root
    injection, accepted ONLY on debug builds (matches this wrapper's
    historical "DEBUG BUILDS ONLY, bare call" ergonomics). Supply a real mac
    (from update_leaf()'s `mac` or apply_offline_operations()'s `root_mac`)
    plus device_id=wallet_id and the attested counter to use the
    production-safe path instead -- verified exactly like fast_forward_root().

    Returns (counter, wallet_id, new_root, applied_count, last_applied_sequence, root_mac)
    -- all reflecting install + replay combined.
    """
    resp = session.call(
        messages.AuthDbSetRoot(
            root=root,
            mac=mac if mac is not None else ZERO_MAC,
            device_id=device_id,
            counter=counter,
            operations=[
                messages.AuthDbRebasedOperation(
                    sequence=op.sequence,
                    address=op.address,
                    old_value=op.old_value,
                    new_value=op.new_value,
                    new_counter=op.new_counter,
                    mac=op.mac,
                    proof=op.proof,
                    witness_address=op.witness_address,
                    witness_value=op.witness_value,
                    old_counter=op.old_counter,
                    witness_counter=op.witness_counter,
                )
                for op in (operations or [])
            ],
        ),
        expect=messages.AuthDbSetRootResponse,
    )
    return (
        resp.counter,
        resp.wallet_id,
        resp.new_root,
        resp.applied_count,
        resp.last_applied_sequence,
        resp.root_mac,
    )


def lookup(
    session: "Session",
    address: bytes,
    value: Optional[bytes],
    proof: list[bytes],
    counter: Optional[int] = None,
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    witness_counter: Optional[int] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify an MPT proof against the stored root.

    For a membership proof supply value + counter (address's leaf counter);
    leave witness_* None. For a non-membership proof supply witness_address,
    witness_counter, and witness_value; value/counter may be None.

    Returns (valid, membership, counter, wallet_id). The response `counter`
    is the ROOT-level counter, not the leaf counter passed in.
    """
    resp = session.call(
        messages.AuthDbLookup(
            address=address,
            value=value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            counter=counter,
            witness_counter=witness_counter,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter, resp.wallet_id


def clear_root(session: "Session") -> Optional[bytes]:
    """Wipe the stored Merkle root. DEBUG BUILDS ONLY.

    Returns wallet_id.
    """
    resp = session.call(
        messages.AuthDbClearRoot(),
        expect=messages.AuthDbClearRootResponse,
    )
    return resp.wallet_id


def update_leaf(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    new_counter: int,
    proof: list[bytes],
    old_counter: Optional[int] = None,
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    witness_counter: Optional[int] = None,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).
    new_counter must be 1 for INSERT/INIT, or old_counter+1 for UPDATE/DELETE
    -- the device enforces this and rejects otherwise (leaf counter, see
    docs/authdb-sync-proposal.md Part 1).
    mac + device_id skip the on-screen confirmation if they match a prior approve() call.

    Returns (counter, new_root, wallet_id, mac, auth_mac).
    new_root/mac are None if tree is now empty.
    auth_mac is set in debug/auto-approve mode: HMAC(device_key, old_leafHash||new_leafHash).
    """
    resp = session.call(
        messages.AuthDbUpdateLeaf(
            address=address,
            old_value=old_value,
            new_value=new_value,
            new_counter=new_counter,
            old_counter=old_counter,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
            mac=mac,
            device_id=device_id,
        ),
        expect=messages.AuthDbUpdateLeafResponse,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.mac, resp.auth_mac


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
    new_value: bytes,
    old_value: Optional[bytes] = None,
) -> tuple[bytes, Optional[bytes]]:
    """Pre-authorize an address old_value->new_value transition on the device.

    old_value=None/b"" means the address is currently absent (INSERT/INIT),
    matching update_leaf's convention -- the MAC is computed the same way
    update_leaf verifies it, so it can only be used to pre-approve this exact
    transition.

    The user confirms on-screen; the device returns a MAC token that can be
    passed to a future update_leaf call for this same address/old_value/
    new_value to skip the confirmation dialog.

    Returns (mac, wallet_id).
    """
    resp = session.call(
        messages.AuthDbApprove(address=address, new_value=new_value, old_value=old_value),
        expect=messages.AuthDbApproveResponse,
    )
    return resp.mac, resp.wallet_id


# ---------------------------------------------------------------------------
# Offline synchronization
# ---------------------------------------------------------------------------

def queue_offline_operation(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    new_counter: int,
    old_counter: Optional[int] = None,
) -> tuple[int, bytes, Optional[bytes]]:
    """Create a signed offline operation when the host database is unreachable.

    old_value=b"" means the address is currently absent (INSERT).
    new_value=b"" means delete the address (DELETE).
    new_counter must be 1 for INSERT, or old_counter+1 otherwise.

    Returns (sequence, mac, wallet_id). Does not touch the Merkle root.
    """
    resp = session.call(
        messages.AuthDbQueueOfflineOperation(
            address=address,
            old_value=old_value,
            new_value=new_value,
            new_counter=new_counter,
            old_counter=old_counter,
        ),
        expect=messages.AuthDbQueueOfflineOperationResponse,
    )
    return resp.sequence, resp.mac, resp.wallet_id


class OfflineOperation:
    """One entry of the on-device offline queue, as returned by get_offline_operations()."""

    def __init__(
        self,
        sequence: int,
        address: bytes,
        old_value: bytes,
        new_value: bytes,
        new_counter: int,
        mac: bytes,
        old_counter: int = 0,
    ) -> None:
        self.sequence = sequence
        self.address = address
        self.old_value = old_value
        self.new_value = new_value
        self.new_counter = new_counter
        self.old_counter = old_counter
        self.mac = mac


def get_offline_operations(
    session: "Session",
) -> tuple[Optional[bytes], int, Optional[bytes], list[OfflineOperation]]:
    """Fetch the current root/counter plus every queued offline operation, for upload.

    Returns (current_root, counter, wallet_id, operations).
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
            new_counter=op.new_counter,
            old_counter=op.old_counter if op.old_counter else 0,
            mac=op.mac,
        )
        for op in resp.operations
    ]
    return resp.current_root, resp.counter, resp.wallet_id, operations


class RebasedOperation:
    """One operation, rebased by the host against the current canonical root.

    sequence/address/old_value/new_value/old_counter/new_counter/mac must be
    forwarded byte-for-byte (value-for-value) from the OfflineOperation it
    originates from -- rebase may choose whether to forward an operation,
    never alter its signed fields. proof/witness_* are freshly computed by
    the host against the root the operation will actually be applied to.
    """

    def __init__(
        self,
        sequence: int,
        address: bytes,
        old_value: bytes,
        new_value: bytes,
        new_counter: int,
        mac: bytes,
        proof: list[bytes],
        old_counter: Optional[int] = None,
        witness_address: Optional[bytes] = None,
        witness_value: Optional[bytes] = None,
        witness_counter: Optional[int] = None,
    ) -> None:
        self.sequence = sequence
        self.address = address
        self.old_value = old_value
        self.new_value = new_value
        self.new_counter = new_counter
        self.old_counter = old_counter
        self.mac = mac
        self.proof = proof
        self.witness_address = witness_address
        self.witness_value = witness_value
        self.witness_counter = witness_counter


def apply_offline_operations(
    session: "Session",
    operations: list[RebasedOperation],
) -> tuple[int, Optional[bytes], int, int, Optional[bytes], Optional[bytes]]:
    """Apply a batch of host-rebased offline operations.

    The device independently verifies each operation's MAC and Merkle proof
    and computes the resulting root itself; it never accepts a host-supplied
    root. Processing stops at the first operation that fails verification or
    is not the immediate next expected sequence.

    Returns (applied_count, new_root, counter, last_applied_sequence,
    wallet_id, root_mac). root_mac is a root-attestation token (absent if
    the tree is now empty) that can be replayed via fast_forward_root() (or
    set_root()'s verified path) on any other physical device sharing this
    wallet.
    """
    resp = session.call(
        messages.AuthDbApplyOfflineOperations(
            operations=[
                messages.AuthDbRebasedOperation(
                    sequence=op.sequence,
                    address=op.address,
                    old_value=op.old_value,
                    new_value=op.new_value,
                    new_counter=op.new_counter,
                    old_counter=op.old_counter,
                    mac=op.mac,
                    proof=op.proof,
                    witness_address=op.witness_address,
                    witness_value=op.witness_value,
                    witness_counter=op.witness_counter,
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
        resp.wallet_id,
        resp.root_mac,
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


def fast_forward_root(
    session: "Session",
    new_root: bytes,
    counter: int,
    wallet_id: bytes,
    mac: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes]]:
    """Fast-forward this wallet's root to a state some device already attested to.

    `mac` must be a root-attestation token previously returned as `mac` from
    update_leaf() or as `root_mac` from apply_offline_operations() -- by this
    device or by any other physical device that has unlocked the same
    wallet_id (the underlying mac_key is wallet-derived, not device-derived).
    Safe on production firmware: a host cannot mint a new token, only replay
    one a device already produced, and the device independently re-derives
    its own mac_key to verify it.

    Returns (counter, new_root, wallet_id).
    """
    resp = session.call(
        messages.AuthDbFastForwardRoot(
            new_root=new_root, counter=counter, wallet_id=wallet_id, mac=mac
        ),
        expect=messages.AuthDbFastForwardRootResponse,
    )
    return resp.counter, resp.new_root, resp.wallet_id


def sync_offline_queue(
    session: "Session",
    persist_and_rebase,
    delete_after_apply: bool = True,
) -> tuple[int, int]:
    """Drive one full offline-sync cycle for this device's active wallet.

    1. Fetch the queue via get_offline_operations().
    2. Call persist_and_rebase(operations) -- caller-supplied callback that
       MUST durably commit each operation to the host's canonical database
       BEFORE returning rebased proofs. This ordering is intentionally hard
       to get wrong: rebased proofs cannot be produced without the caller
       already having the canonical (post-write) tree state, which for a
       real backend implies the write already landed.
    3. apply_offline_operations() -- device verifies + applies, returns
       last_applied_sequence.
    4. If delete_after_apply and applied_count > 0: delete_offline_operations().
       Pass delete_after_apply=False to apply now and delete in a later,
       separate call (e.g. after an out-of-band durability confirmation such
       as a DB replica ack) -- apply and delete are intentionally separate
       RPCs, so this wrapper preserves that separation instead of hiding it.

    Returns (applied_count, deleted_count) (deleted_count=0 if skipped).
    """
    _current_root, _counter, _wallet_id, operations = get_offline_operations(session)
    if not operations:
        return 0, 0

    rebased = persist_and_rebase(operations)
    applied_count, _new_root, _counter, _last_applied_sequence, _wallet_id, _root_mac = (
        apply_offline_operations(session, rebased)
    )

    deleted_count = 0
    if delete_after_apply and applied_count > 0:
        deleted_count, _remaining = delete_offline_operations(session)

    return applied_count, deleted_count
