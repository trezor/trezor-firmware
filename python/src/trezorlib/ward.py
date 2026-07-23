from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from . import _ed25519, messages

if TYPE_CHECKING:
    from .transport.session import Session

ZERO_MAC = b"\x00" * 32

# WARD attestation domains (must match apps.authdb._qm).
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"
_WARD_ATTEST_DOMAIN = b"WARD ATTEST v1"
_WARD_ATTEST_VERSION = 1

# Well-known DEBUG WM/QM Ed25519 seed, accepted only by debug firmware. Its public
# key is provisioned as _QM_PUBKEY_DEBUG in core/src/apps/authdb/_qm.py. Used by
# tests / the CLI to stand in for the WARD Manager's final signature.
DEBUG_QM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD write round (set_entry -> commit -> finalize)
# ---------------------------------------------------------------------------


def set_entry(
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
        messages.WARDSetEntry(
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
        expect=messages.WARDSetEntryAck,
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


def finalize(
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


def sign_ward_final(
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
# Wire wrappers — the WARD sync round (bootstrap/refresh) + lookup + debug seed
# ---------------------------------------------------------------------------


def init_sync(session: "Session") -> tuple[bytes, int, Optional[bytes]]:
    """Begin a sync round. Returns (nonce, version, wallet_id)."""
    resp = session.call(
        messages.WARDInitSyncRound(), expect=messages.WARDInitSyncRoundAck
    )
    return resp.nonce, resp.version, resp.wallet_id


def ingest_attestation(
    session: "Session", counter: int, mac: Optional[bytes], wm_signature: bytes
) -> tuple[int, Optional[bytes]]:
    """Deliver the WM freshness attestation. Returns (counter, wallet_id)."""
    resp = session.call(
        messages.WARDIngestAttestation(
            counter=counter, mac=mac, wm_signature=wm_signature
        ),
        expect=messages.WARDIngestAttestationAck,
    )
    return resp.counter, resp.wallet_id


def list_pending(session: "Session") -> tuple[list[bytes], Optional[bytes]]:
    """Return (pending_edit_addresses, wallet_id)."""
    resp = session.call(
        messages.WARDListPendingEdits(), expect=messages.WARDListPendingEditsAck
    )
    return list(resp.addresses), resp.wallet_id


def merge_state(
    session: "Session", root: Optional[bytes]
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Adopt the attested root. Returns (counter, new_root, wallet_id, root_mac)."""
    resp = session.call(
        messages.WARDMergeState(root=root), expect=messages.WARDMergeStateAck
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


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


def bootstrap(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    root: Optional[bytes],
    sign_attestation: Optional[Callable[[bytes, bytes, int, bytes], bytes]] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Run a full sync round: init_sync -> (WM sign) -> ingest_attestation ->
    merge_state, adopting the WM-attested (counter, mac) and host `root`.

    `sign_attestation(wallet_id, nonce, counter, mac) -> signature` is the WM's
    freshness attestation; defaults to the debug signer. Returns merge_state's
    (counter, new_root, wallet_id, root_mac).
    """
    nonce, _version, wallet_id = init_sync(session)
    assert wallet_id is not None
    mac_for_sig = mac if mac is not None else ZERO_MAC
    if sign_attestation is not None:
        sig = sign_attestation(wallet_id, nonce, counter, mac_for_sig)
    else:
        sig = sign_wm_attestation(nonce, counter, mac_for_sig, wallet_id)
    ingest_attestation(session, counter, mac, sig)
    return merge_state(session, root)


# ---------------------------------------------------------------------------
# Convenience: the whole write round in one call (drop-in for the former
# authdb.update_leaf). Returns the same (counter, new_root, wallet_id, mac) shape.
# ---------------------------------------------------------------------------


def write(
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
    sign_final: Optional[Callable[[bytes, int, bytes], bytes]] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Run set_entry -> commit -> (WM sign) -> finalize.

    `sign_final(wallet_id, counter, mac) -> signature` is the WM's final
    attestation; defaults to the debug signer. Returns
    (counter, new_root, wallet_id, root_mac).
    """
    set_entry(
        session,
        address,
        old_value,
        new_value,
        new_counter,
        proof,
        old_counter=old_counter,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )
    c_counter, root_t, mac_t, wallet_id = commit(session)
    mac_for_sig = mac_t if mac_t is not None else ZERO_MAC
    assert wallet_id is not None
    if sign_final is not None:
        sig = sign_final(wallet_id, c_counter, mac_for_sig)
    else:
        sig = sign_ward_final(c_counter, mac_for_sig, wallet_id)
    return finalize(session, c_counter, mac_t, sig)
