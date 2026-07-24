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


def add_pending(
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
) -> tuple[int, Optional[bytes]]:
    """Verify a leaf change and queue it as the PENDING candidate.

    old_value=b"" means the address is currently absent (INSERT / INIT);
    new_value=b"" means delete (DELETE). new_counter must equal the current root
    counter + 1. The device computes the candidate root/MAC but does NOT advance
    its counter. Returns (candidate_counter, wallet_id).
    """
    resp = session.call(
        messages.WARDAddPending(
            address=address,
            old_value=old_value,
            new_value=new_value,
            new_counter=new_counter,
            old_counter=old_counter,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
        ),
        expect=messages.WARDAddPendingAck,
    )
    return resp.counter, resp.wallet_id


def commit(
    session: "Session",
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Emit the queued candidate. Returns (counter_T, root_T, mac_T, wallet_id);
    root_T/mac_T are None if the candidate empties the tree."""
    resp = session.call(
        messages.WARDCommitCandidate(), expect=messages.WARDCommitCandidateAck
    )
    return resp.counter, resp.new_root, resp.mac, resp.wallet_id


def confirm_commit(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    qm_signature: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Finalize the committed candidate with the WM's Ed25519 signature.

    Advances the device counter and drops the queue. Returns
    (counter, new_root, wallet_id, root_mac).
    """
    resp = session.call(
        messages.WARDConfirmCommit(counter=counter, mac=mac, qm_signature=qm_signature),
        expect=messages.WARDConfirmCommitAck,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


def discard_pending(
    session: "Session",
) -> tuple[Optional[bytes], Optional[bytes]]:
    """Abandon the current wallet's queued pending edit without finalizing it,
    unblocking the depth-1 offline queue. Returns (discarded_address, wallet_id);
    discarded_address is None if nothing was queued for this wallet."""
    resp = session.call(
        messages.WARDDiscardPending(), expect=messages.WARDDiscardPendingAck
    )
    return resp.discarded_address, resp.wallet_id


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD sync round + lookup + debug seed
# ---------------------------------------------------------------------------


def sync(session: "Session") -> bytes:
    """Start a fresh sync round on the device.

    Returns the fresh nonce for WM attestation. Suite/host already knows the
    wallet identity and carries it to the WM out-of-band.
    """
    resp = session.call(
        messages.WARDSync(), expect=messages.WARDSyncAck
    )
    return resp.nonce


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
    address: bytes,
    value: Optional[bytes],
    proof: list[bytes],
    counter: Optional[int] = None,
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    witness_counter: Optional[int] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify a proof against the device's authenticated root (formerly
    authdb.lookup). Returns (valid, membership, counter, wallet_id)."""
    resp = session.call(
        messages.WARDLookup(
            address=address,
            value=value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            counter=counter,
            witness_counter=witness_counter,
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


def build_proof_ack(tree: "WARDTree", address: bytes) -> messages.WARDProofAck:
    """Answer a WARDProofRequest from `tree`: a membership proof if the address is
    present, otherwise a non-membership (witness) proof, or an empty ack for an
    empty tree."""
    if tree.is_empty():
        return messages.WARDProofAck()
    if tree.get_counter(address):
        return messages.WARDProofAck(
            value=tree.get_value(address),
            proof=tree.get_proof(address),
            counter=tree.get_counter(address),
        )
    proof, witness_address, witness_counter, witness_value = (
        tree.get_nonmembership_proof(address)
    )
    return messages.WARDProofAck(
        proof=proof,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )


def tree_proof_callback(
    tree: "WARDTree",
) -> Callable[[messages.WARDProofRequest], messages.WARDProofAck]:
    """Build an AppManifest.ward_proof_callback that serves proofs from `tree`.

    Register it on the client so the device can pull WARD proofs on demand:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    """

    def _callback(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        return build_proof_ack(tree, msg.address)

    return _callback
