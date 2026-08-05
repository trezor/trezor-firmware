from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from . import messages

if TYPE_CHECKING:
    from .authdb_tree import WARDTree
    from .transport.session import Session

ZERO_MAC = b"\x00" * 32

# NOTE: the WM (WARD Manager) signing helpers and the debug WM key are NOT here.
# They are the WARD Manager's role (an external freshness authority), not a
# device-client operation, and they forge signatures with a debug-only key. They
# live in the test harness at tests/ward_mgr_emu.py so this production client
# library ships no debug-only signing.


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD update round (add_pending -> commit -> finalize)
# ---------------------------------------------------------------------------


def queue_update(
    session: "Session",
    app_id: str,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    key_type: str = "address",
    device_id: int = 0,
) -> tuple[Optional[int], Optional[bytes]]:
    """Queue an edit INTENT (pull model). Carries NO proof.

    old_value=b"" means the address is currently absent (INSERT); new_value=b""
    means delete (DELETE); old_value is a display hint only. The device shows the
    old -> new change on a trusted screen and, only on user approval, returns a
    pending_id. Under the strict model NO candidate counter is derived here; the
    counter and candidate root are computed later, at perform_update, from a proof
    the device pulls itself. Returns (pending_id, wallet_id).
    """
    # old_value is a display hint only and is not carried on the wire (the diagram's
    # WARDQueueUpdate is address + new_value); the device pulls the current state at
    # perform time.
    del old_value
    resp = session.call(
        messages.WARDQueueUpdate(
            app_id=app_id,
            address=address,
            new_value=new_value,
            key_type=key_type,
            device_id=device_id,
        ),
        expect=messages.WARDQueueUpdateAck,
    )
    return resp.pending_id, resp.wallet_id


def perform_update(
    session: "Session",
    pending_id: Optional[int] = None,
) -> tuple:
    """Authorize a queued intent. The device PULLS the proof it needs mid-call:
    it emits a WARDProofRequest, which the client answers via the registered
    ``ward_proof_callback`` (e.g. ``tree_proof_callback(tree)``) -- so a callback
    MUST be registered before calling this. This is where the device first derives
    counter_T (strict model). pending_id selects the intent; if omitted, the device
    targets the single queued one.

    The device is the encryptor, so it also returns the new leaf blob
    (entry_key, entry_type, nonce, tag, ct) it produced — the host cannot compute it
    and must store it keyed by entry_key (ct empty => DELETE). Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id, entry_key, entry_type, nonce, tag, ct);
    root_T/mac_T are None if the candidate empties the tree.
    """
    resp = session.call(
        messages.WARDPerformUpdate(pending_id=pending_id),
        expect=messages.WARDPerformUpdateAck,
    )
    return (
        resp.counter,
        resp.new_root,
        resp.mac,
        resp.wallet_id,
        resp.ward_id,
        resp.entry_key,
        resp.entry_type,
        resp.nonce,
        resp.tag,
        resp.ct,
    )


def confirmed_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
    pending_id: Optional[int] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a committed candidate with the WM's Ed25519 signature over the exact
    device-derived (counter_T, mac_T). pending_id selects it; if omitted, the
    device targets the single queued candidate.

    Advances the device counter and drops that candidate. Returns
    (counter, new_root, wallet_id, root_mac).
    """
    resp = session.call(
        messages.WARDConfirmedByWM(
            counter=counter, mac=mac, wm_signature=wm_signature, pending_id=pending_id
        ),
        expect=messages.WARDConfirmedByWMAck,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


def perform_batch(session: "Session", pending_ids: list) -> tuple:
    """Authorize N queued intents as ONE root transition (batch-update). The device
    PULLS one proof per intent (WARDProofRequest per entry_key), answered by the
    registered ``ward_proof_callback`` — so a callback MUST be registered first. The
    whole batch advances the counter by 1. Returns (counter, from_root, new_root, mac,
    wallet_id, ward_id, head_mac, auth_commit, sig_commit, leaves) where `leaves` is a
    list of (entry_key, entry_type, nonce, tag, ct) the host stores keyed by entry_key
    (ct empty => DELETE)."""
    resp = session.call(
        messages.WARDPerformBatch(pending_ids=pending_ids),
        expect=messages.WARDPerformBatchAck,
    )
    leaves = [
        (lf.entry_key, lf.entry_type, lf.nonce, lf.tag, lf.ct) for lf in resp.leaves
    ]
    return (
        resp.counter,
        resp.from_root,
        resp.new_root,
        resp.mac,
        resp.wallet_id,
        resp.ward_id,
        resp.head_mac,
        resp.auth_commit,
        resp.sig_commit,
        leaves,
    )


def confirmed_batch_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a committed batch with the WM's Ed25519 signature over the exact
    device-derived (to_counter, mac_t). Advances the counter by 1 and drops the whole
    pending set. Returns (counter, new_root, wallet_id, root_mac)."""
    resp = session.call(
        messages.WARDConfirmBatchByWM(
            counter=counter, mac=mac, wm_signature=wm_signature
        ),
        expect=messages.WARDConfirmBatchByWMAck,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


def perform_revert(
    session: "Session",
    stuck_counter: int,
    stuck_root: Optional[bytes],
    prev_root: Optional[bytes],
    forward_auth_commit: bytes,
) -> tuple:
    """Prepare a constrained one-step rollback (ward-design §8.2). Presents the
    FORWARD AuthCommit that created the current stuck head plus the predecessor root
    it encodes; the device verifies that MAC to prove the predecessor and demotes with
    a FORWARD-incrementing counter (to_counter = stuck_counter + 1). Returns (counter,
    from_root, new_root, mac, wallet_id, ward_id, head_mac, auth_revert, sig_commit)."""
    resp = session.call(
        messages.WARDPerformRevert(
            stuck_counter=stuck_counter,
            stuck_root=stuck_root,
            prev_root=prev_root,
            forward_auth_commit=forward_auth_commit,
        ),
        expect=messages.WARDPerformRevertAck,
    )
    return (
        resp.counter,
        resp.from_root,
        resp.new_root,
        resp.mac,
        resp.wallet_id,
        resp.ward_id,
        resp.head_mac,
        resp.auth_revert,
        resp.sig_commit,
    )


def confirmed_revert_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a one-step rollback with the WM's signature over (to_counter, mac_t).
    Returns (counter, new_root, wallet_id, root_mac)."""
    resp = session.call(
        messages.WARDConfirmRevertByWM(
            counter=counter, mac=mac, wm_signature=wm_signature
        ),
        expect=messages.WARDConfirmRevertByWMAck,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


def discard_pending(
    session: "Session",
    pending_id: Optional[int] = None,
) -> tuple[Optional[bytes], Optional[bytes]]:
    """Abandon queued pending edit(s) without finalizing. With pending_id, drops
    just that candidate; without it, drops EVERY candidate queued for the wallet.
    Returns (discarded_address, wallet_id); discarded_address is None when nothing
    matched (or in drop-all mode)."""
    resp = session.call(
        messages.WARDDiscardPending(pending_id=pending_id),
        expect=messages.WARDDiscardPendingAck,
    )
    return resp.discarded_address, resp.wallet_id


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD sync round + lookup + debug seed
# ---------------------------------------------------------------------------


def sync(session: "Session") -> tuple[bytes, Optional[bytes]]:
    """Start a fresh sync round on the device.

    Returns (nonce, ward_id): the fresh nonce for WM attestation and the
    SLIP21-derived WM-facing ward_id the host forwards to the WM (the WM signs its
    attestation preimage over ward_id, not the local wallet_id).
    """
    resp = session.call(
        messages.WARDSync(), expect=messages.WARDSyncAck
    )
    return resp.nonce, resp.ward_id


def ingest_attestation(
    session: "Session",
    counter_ext: int,
    root_mac_ext: Optional[bytes],
    wm_signature: bytes,
) -> int:
    """Verify and record the WM freshness attestation for the open sync round.

    Returns the accepted external counter.
    """
    resp = session.call(
        messages.WARDIngestAttestation(
            counter=counter_ext, mac=root_mac_ext, wm_signature=wm_signature
        ),
        expect=messages.WARDIngestAttestationAck,
    )
    return resp.counter


def list_pending(session: "Session") -> tuple[list[bytes], Optional[bytes]]:
    """Return (pending_edit_addresses, wallet_id).

    Note:
    - wallet_id is returned only for current compatibility
    - callers should not rely on list_pending() as the source of wallet_id
    - the intended design is for wallet_id to come from a different host/device source
    """
    resp = session.call(
        messages.WARDListPendingEdits(), expect=messages.WARDListPendingEditsAck
    )
    return list(resp.addresses), resp.wallet_id


def reconcile(
    session: "Session", root: Optional[bytes]
) -> tuple[int, Optional[bytes], Optional[bytes]]:
    """Finalize an already-attested sync round by installing the supplied root.

    Returns (counter, adopted_root, installed_root_mac).
    """
    resp = session.call(
        messages.WARDReconcile(root=root), expect=messages.WARDReconcileAck
    )
    return resp.counter, resp.new_root, resp.root_mac


def lookup(
    session: "Session",
    app_id: str,
    address: bytes,
    proof: list[bytes],
    nonce: Optional[bytes] = None,
    tag: Optional[bytes] = None,
    ct: Optional[bytes] = None,
    key_type: str = "address",
    device_id: int = 0,
    witness_entry_key: Optional[bytes] = None,
    witness_commit: Optional[bytes] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """PUSH-verify a proof against the device's authenticated root. Returns
    (valid, membership, counter, wallet_id). The device forms
    entry_key = HMAC(K_index, app_id||0x00||key_type||0x00||device_id||address) and,
    for membership, rebuilds the leaf from (nonce, tag, ct); a non-membership witness
    is two hashes only (witness_entry_key, witness_commit)."""
    resp = session.call(
        messages.WARDLookup(
            app_id=app_id,
            address=address,
            proof=proof,
            nonce=nonce,
            tag=tag,
            ct=ct,
            key_type=key_type,
            device_id=device_id,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
        ),
        expect=messages.WARDLookupAck,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter, resp.wallet_id


def export_keys(
    session: "Session", key_type: str = "address"
) -> tuple[Optional[bytes], Optional[bytes], Optional[str]]:
    """PUSH: retrieve the keys the host needs to serve the push flow itself —
    K_index (to compute entry_key from a plaintext identifier) and K_data(key_type)
    (to encrypt/decrypt values). K_sig is never exported. The host should keep the
    returned keys in memory only. Returns (k_index, k_data, key_type)."""
    resp = session.call(
        messages.WARDExportKeys(key_type=key_type),
        expect=messages.WARDExportKeysAck,
    )
    return resp.k_index, resp.k_data, resp.key_type


def debug_set_root(
    session: "Session", root: bytes
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """DEBUG-only unauthenticated root injection (seeds a root in one call).
    Returns (counter, new_root, wallet_id, root_mac)."""
    resp = session.call(
        messages.WARDDebugSetRoot(root=root), expect=messages.WARDDebugSetRootAck
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


# ---------------------------------------------------------------------------
# Proof-on-demand: the device pulls a WARD proof mid-workflow via WARDProofRequest.
# ---------------------------------------------------------------------------


def build_proof_ack(tree: "WARDTree", entry_key: bytes) -> messages.WARDProofAck:
    """Answer a WARDProofRequest by the opaque `entry_key` path (pull model): a
    membership proof (entry_type + nonce/tag/ct + proof) if the leaf is present,
    otherwise a non-membership witness (witness_entry_key, witness_commit), or an
    empty ack for an empty tree. The host serves purely by entry_key and never
    learns the identifier or the plaintext value (§3)."""
    if tree.is_empty():
        return messages.WARDProofAck()
    leaf = tree.get_leaf(entry_key)
    if leaf is not None:
        nonce, tag, ct, entry_type = leaf
        return messages.WARDProofAck(
            proof=tree.get_proof_by_key(entry_key),
            entry_type=entry_type,
            nonce=nonce,
            tag=tag,
            ct=ct,
        )
    proof, witness_entry_key, witness_commit = tree.get_nonmembership_proof_by_key(
        entry_key
    )
    return messages.WARDProofAck(
        proof=proof,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


def tree_proof_callback(
    tree: "WARDTree",
) -> Callable[[messages.WARDProofRequest], messages.WARDProofAck]:
    """Build an AppManifest.ward_proof_callback that serves proofs from `tree`.

    Register it on the client so the device can pull WARD proofs on demand:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    """

    def _callback(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        # The device sends the opaque entry_key path; serve the proof for it.
        return build_proof_ack(tree, msg.entry_key)

    return _callback
