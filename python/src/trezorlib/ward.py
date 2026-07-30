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
        ),
        expect=messages.WARDQueueUpdateAck,
    )
    return resp.pending_id, resp.wallet_id


def perform_update(
    session: "Session",
    pending_id: Optional[int] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Authorize a queued intent. The device PULLS the proof it needs mid-call:
    it emits a WARDProofRequest, which the client answers via the registered
    ``ward_proof_callback`` (e.g. ``tree_proof_callback(tree)``) -- so a callback
    MUST be registered before calling this. This is where the device first derives
    counter_T (strict model). pending_id selects the intent; if omitted, the device
    targets the single queued one. Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id); root_T/mac_T are None if the
    candidate empties the tree.
    """
    resp = session.call(
        messages.WARDPerformUpdate(pending_id=pending_id),
        expect=messages.WARDPerformUpdateAck,
    )
    return resp.counter, resp.new_root, resp.mac, resp.wallet_id, resp.ward_id


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
    value: Optional[bytes],
    proof: list[bytes],
    counter: Optional[int] = None,
    witness_entry_key: Optional[bytes] = None,
    witness_value_hash: Optional[bytes] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify a proof against the device's authenticated root (formerly
    authdb.lookup). Returns (valid, membership, counter, wallet_id). The device forms
    entry_key(app_id, address); a non-membership witness is two hashes only."""
    resp = session.call(
        messages.WARDLookup(
            app_id=app_id,
            address=address,
            value=value,
            proof=proof,
            witness_entry_key=witness_entry_key,
            witness_value_hash=witness_value_hash,
            counter=counter,
        ),
        expect=messages.WARDLookupAck,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter, resp.wallet_id


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


def build_proof_ack(
    tree: "WARDTree", app_id: str, address: bytes
) -> messages.WARDProofAck:
    """Answer a WARDProofRequest from `tree` within the domain named by app_id: a
    membership proof if the entry is present, otherwise a non-membership (witness)
    proof, or an empty ack for an empty tree. The witness is two hashes only
    (witness_entry_key, witness_value_hash) — no plaintext leaks across apps."""
    if tree.is_empty():
        return messages.WARDProofAck(app_id=app_id)
    if tree.get_counter(app_id, address):
        return messages.WARDProofAck(
            value=tree.get_value(app_id, address),
            proof=tree.get_proof(app_id, address),
            counter=tree.get_counter(app_id, address),
            app_id=app_id,
        )
    proof, witness_entry_key, witness_value_hash = tree.get_nonmembership_proof(
        app_id, address
    )
    return messages.WARDProofAck(
        proof=proof,
        witness_entry_key=witness_entry_key,
        witness_value_hash=witness_value_hash,
        app_id=app_id,
    )


def tree_proof_callback(
    tree: "WARDTree",
) -> Callable[[messages.WARDProofRequest], messages.WARDProofAck]:
    """Build an AppManifest.ward_proof_callback that serves proofs from `tree`.

    Register it on the client so the device can pull WARD proofs on demand:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    """

    def _callback(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        # The device names the domain in the request; serve the proof for it.
        return build_proof_ack(tree, msg.app_id or "", msg.address)

    return _callback
