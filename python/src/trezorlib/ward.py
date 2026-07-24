from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import _ed25519, messages

if TYPE_CHECKING:
    from .transport.session import Session

ZERO_MAC = b"\x00" * 32

# WARD attestation domains (must match apps.authdb._qm).
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"
_WARD_ATTEST_DOMAIN = b"WARD ATTEST v1"
_WARD_ATTEST_VERSION = 1

# Well-known DEBUG WM/QM Ed25519 seed, accepted only by debug firmware. Its public
# key is provisioned as _WM_PUBKEY_DEBUG in core/src/apps/ward/service.py. Used by
# tests / the CLI to stand in for the WARD Manager's final signature.
DEBUG_QM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."


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


# ---------------------------------------------------------------------------
# WM final-attestation signing (dev/test helper)
# ---------------------------------------------------------------------------


def sign_ward_update(
    counter: int, mac: bytes, wallet_id: bytes, qm_seed: bytes = DEBUG_QM_SEED
) -> bytes:
    """Produce the WM final attestation the device verifies in WARDConfirmCommit:

        Ed25519-Sign(qm_seed, b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac)

    In production the WARD Manager holds the key and signs; this dev helper signs
    with the debug seed so tests / the CLI can drive the full flow.
    """
    message = _WARD_FINAL_DOMAIN + wallet_id + counter.to_bytes(4, "big") + mac
    pk = _ed25519.publickey_unsafe(qm_seed)
    return _ed25519.signature_unsafe(message, qm_seed, pk)


def sign_wm_attestation(
    nonce: bytes,
    counter: int,
    mac: bytes,
    wallet_id: bytes,
    qm_seed: bytes = DEBUG_QM_SEED,
) -> bytes:
    """Produce the WM freshness attestation the device verifies in
    WARDIngestAttestation:

        Ed25519-Sign(qm_seed,
            b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac)

    Dev helper: signs with the debug WM seed so tests/CLI can drive the sync round.
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + wallet_id
        + counter.to_bytes(4, "big")
        + mac
    )
    pk = _ed25519.publickey_unsafe(qm_seed)
    return _ed25519.signature_unsafe(message, qm_seed, pk)


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
    """Return (pending_edit_addresses, wallet_id)."""
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
