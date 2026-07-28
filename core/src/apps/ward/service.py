"""WARD service — the on-device trust anchor (TW), as a single module.

Consolidates the WARD trust-anchor logic that was previously split across
apps.authdb._mpt (MPT proof/root primitives), apps.authdb._qm (WM attestation
verification), apps.authdb.__init__ (wallet/MAC derivation) and apps.ward.__init__
(queue + root helpers), plus the write/lookup orchestration that used to live
inline in the message handlers.

Layering:
  - persistence  -> storage.ward_store (counter, authenticated root, queue, sync ctx)
  - callers      -> apps.common.ward (Core capability boundary) and the thin
                    host-facing protobuf handlers in apps.ward.*

The authenticity/freshness primitives are implemented and audited exactly once
here; production firmware never accepts a host-supplied root.
"""

from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# WM (WARD Manager / QM) Ed25519 attestation keys + domains.
#
# The WM owns the authoritative per-wallet (counter, mac). The device verifies
# its signatures against a provisioned WM public key before trusting attested
# state. Preimages:
#   - freshness/ingest (WARDIngestAttestation):
#       b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac
#   - final/install (WARDConfirmedByWM):
#       b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac
# ---------------------------------------------------------------------------

# PLACEHOLDER production key (all-zero): production firmware rejects every WM
# signature until a real WM public key is provisioned here.
_WM_PUBKEY = b"\x00" * 32

if __debug__:
    from ubinascii import unhexlify

    # Well-known debug WM public key, accepted only on debug builds. Its 32-byte
    # Ed25519 private seed is the ASCII string b"AUTHDB QM DEBUG KEY SEED v1 ....";
    # tests/tools sign attestations with it.
    _WM_PUBKEY_DEBUG = unhexlify(
        b"17b4c21f6b55935405d5a48ee3f2f29f42d78c9a650d8f686a705b21ef62b0b6"
    )

_WARD_ATTEST_DOMAIN = b"WARD ATTEST v1"
_WARD_ATTEST_VERSION = const(1)
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"

# WARD protocol version echoed in the sync round (WARDSyncAck).
_WARD_VERSION = const(1)
# All-zero MAC == the candidate/attested state that empties the tree.
_ZERO_MAC = b"\x00" * 32


# ---------------------------------------------------------------------------
# MPT hash / proof primitives (formerly apps.authdb._mpt).
#
# Leaf hash = sha256d(0x00||address||counter(4B BE)||value); counter is the
# GLOBAL root counter stamped onto the leaf on change. compute_new_root() is the
# single INIT/INSERT/UPDATE/DELETE state machine; it does not enforce the
# per-generation +1 rule -- update_entry() does that.
# ---------------------------------------------------------------------------


def sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


def addr_bit(addr_hash: bytes, bit: int) -> int:
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def leaf_hash(address: bytes, counter: int, value: bytes) -> bytes:
    return sha256d(b"\x00" + address + counter.to_bytes(4, "big") + value)


def internal_hash(left: bytes, right: bytes) -> bytes:
    return sha256d(b"\x01" + left + right)


def reconstruct(start_hash: bytes, proof: list, addr_hash: bytes) -> bytes:
    """Walk proof from leaf toward root, rebuilding hashes."""
    node = start_hash
    for elem in proof:
        bit = elem[0]
        sibling = bytes(elem[1:])
        if addr_bit(addr_hash, bit) == 0:
            node = internal_hash(node, sibling)
        else:
            node = internal_hash(sibling, node)
    return node


def verify_proof(
    address: bytes,
    counter: int,
    value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify an MPT membership proof for (address, counter, value) against expected_root."""
    addr_hash = sha256d(address)
    node = leaf_hash(address, counter, value)
    node = reconstruct(node, proof, addr_hash)
    return node == expected_root


def verify_nonmembership(
    address: bytes,
    witness_address: bytes,
    witness_counter: int,
    witness_value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify that address is NOT in the tree.

    The caller supplies a witness leaf (witness_address, witness_counter,
    witness_value) that occupies address's path in the tree. We verify:
      1. The witness is in the tree (membership proof against stored root).
      2. witness_address != address.
      3. witness_address and address share the same bit-value at every bit
         position that appears in the proof (they diverge only after the
         deepest branch, i.e. the witness is truly the closest leaf to
         address).
    """
    if witness_address == address:
        return False

    addr_hash = sha256d(address)
    witness_hash = sha256d(witness_address)

    for elem in proof:
        bit = elem[0]
        if addr_bit(addr_hash, bit) != addr_bit(witness_hash, bit):
            return False

    return verify_proof(witness_address, witness_counter, witness_value, proof, expected_root)


def compute_new_root(
    address: bytes,
    old_counter: int,
    old_value: bytes,
    new_counter: int,
    new_value: bytes,
    proof: list,
    stored_root,
    witness_address=None,
    witness_counter=None,
    witness_value=None,
):
    """Verify (old_counter, old_value, proof) against stored_root, then compute
    the new root. Returns the new root (None if the tree becomes/stays empty),
    or raises ValueError if the old-state proof does not verify. Single
    implementation of the INIT/INSERT/UPDATE/DELETE state machine; update_entry()
    enforces new_counter == current root counter + 1.
    """
    inserting = len(old_value) == 0
    deleting = len(new_value) == 0
    if inserting and deleting:
        raise ValueError("old_value and new_value cannot both be empty")

    addr_hash = sha256d(address)

    if inserting:
        if len(proof) == 0 and witness_address is None:
            # INIT: tree was empty
            if stored_root is not None:
                raise ValueError("Tree is not empty; supply non-membership proof")
            return leaf_hash(address, new_counter, new_value)

        if witness_address is None or witness_counter is None or witness_value is None:
            raise ValueError("witness_address/witness_counter/witness_value required for INSERT")
        if witness_address == address:
            raise ValueError("witness_address must differ from address")

        witness_hash = sha256d(witness_address)
        for elem in proof:
            bit = elem[0]
            if addr_bit(addr_hash, bit) != addr_bit(witness_hash, bit):
                raise ValueError("Witness does not occupy target's path")

        witness_in_tree = reconstruct(
            leaf_hash(witness_address, witness_counter, witness_value), proof, witness_hash
        )
        if witness_in_tree != stored_root:
            raise ValueError("Non-membership proof invalid: witness not in tree")

        split_bit = None
        for b in range(256):
            if addr_bit(addr_hash, b) != addr_bit(witness_hash, b):
                split_bit = b
                break
        if split_bit is None:
            raise ValueError("address and witness_address hash to same value")

        new_leaf_t = leaf_hash(address, new_counter, new_value)
        new_leaf_w = leaf_hash(witness_address, witness_counter, witness_value)
        if addr_bit(addr_hash, split_bit) == 0:
            new_branch = internal_hash(new_leaf_t, new_leaf_w)
        else:
            new_branch = internal_hash(new_leaf_w, new_leaf_t)
        return reconstruct(new_branch, proof, witness_hash)

    if deleting:
        if stored_root is None:
            raise ValueError("No Merkle root stored on device")
        current_leaf = leaf_hash(address, old_counter, old_value)
        if reconstruct(current_leaf, proof, addr_hash) != stored_root:
            raise ValueError("Old value proof invalid")
        if len(proof) == 0:
            return None
        sibling_hash = bytes(proof[0][1:])
        return reconstruct(sibling_hash, proof[1:], addr_hash)

    # UPDATE (new_counter is the global stamp; validated by update_entry)
    if stored_root is None:
        raise ValueError("No Merkle root stored on device")
    current_leaf = leaf_hash(address, old_counter, old_value)
    if reconstruct(current_leaf, proof, addr_hash) != stored_root:
        raise ValueError("Old value proof invalid")
    return reconstruct(leaf_hash(address, new_counter, new_value), proof, addr_hash)


# ---------------------------------------------------------------------------
# WM attestation verification (formerly apps.authdb._qm).
# ---------------------------------------------------------------------------


def _verify(message: bytes, signature: bytes) -> bool:
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    if ed25519.verify(_WM_PUBKEY, signature, message):
        return True
    if __debug__:
        return ed25519.verify(_WM_PUBKEY_DEBUG, signature, message)
    return False


def verify_wm_attestation(
    ward_id: bytes, nonce: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's freshness attestation for a sync round:

        b"WARD ATTEST v1" || version(1B) || nonce || ward_id || counter(4B BE) || mac

    `ward_id` is the SLIP21-derived WM-facing anchor (see `_get_ward_id`), NOT the
    20-byte local `wallet_id`; the WM only ever signs over `ward_id`.
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + ward_id
        + counter.to_bytes(4, "big")
        + mac
    )
    return _verify(message, signature)


def verify_ward_final(
    ward_id: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's final attestation over the committed WARD candidate:

        b"WARD FINAL v1" || ward_id || counter(4B BE) || mac

    `ward_id` is the SLIP21-derived WM-facing anchor (see `_get_ward_id`).
    """
    message = _WARD_FINAL_DOMAIN + ward_id + counter.to_bytes(4, "big") + mac
    return _verify(message, signature)


# ---------------------------------------------------------------------------
# Wallet identity + MAC derivation (formerly apps.authdb.__init__).
# ---------------------------------------------------------------------------


async def _get_wallet_id() -> bytes:
    """wallet_id = RIPEMD160(SHA256(compressed master public key)) -- 20 bytes.

    The BIP32 identifier (Hash160) of the wallet's master xpub, derived from the
    passphrase-including seed, so distinct hidden wallets get distinct trees.
    """
    from trezor.crypto import bip32
    from trezor.crypto.scripts import sha256_ripemd160
    from apps.common import seed as seed_module

    s = await seed_module.get_seed()
    node = bip32.from_seed(s, "secp256k1")
    return sha256_ripemd160(node.public_key()).digest()


async def _get_ward_id() -> bytes:
    """ward_id = SLIP21(seed, [b"TREZOR", b"WARDID", b"wallet_id", wallet_id]).key()
    -- 32 bytes.

    The WM-facing anti-rollback / anti-fork anchor (spec §5). Distinct from the
    20-byte local `wallet_id`: it is what the WM signs over in every ATTEST/FINAL
    preimage, is derived from the seed (so it is wallet-stable and independent of
    the mutable Evolu `ownerId`), and is verifiable by the device. The device
    derives it and forwards it to the host; the host MUST NOT invent or substitute
    it.
    """
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    wallet_id = await _get_wallet_id()
    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"TREZOR", b"WARDID", b"wallet_id", wallet_id])
    return node.key()


async def _derive_mac_key(domain: bytes) -> bytes:
    """mac_key = HMAC-SHA256(SLIP21(seed, [b"AUTHDB MAC v1", domain]).key(), wallet_id).

    `domain` (currently only b"root_mac") is folded into the SLIP-21 path so each
    purpose gets a distinct base key; bound to wallet_id so a MAC minted for one
    hidden wallet never validates against another's tree.
    """
    from trezor.crypto import hmac as crypto_hmac

    wallet_id = await _get_wallet_id()

    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB MAC v1", domain])
    base_key = node.key()

    return crypto_hmac(crypto_hmac.SHA256, base_key, wallet_id).digest()


def _compute_mac(key: bytes, *parts: bytes) -> bytes:
    """HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()


# ---------------------------------------------------------------------------
# Root/MAC + pending-queue helpers (formerly apps.ward.__init__).
# ---------------------------------------------------------------------------


def compute_root(
    address: bytes,
    old_counter: int,
    old_value: bytes,
    new_counter: int,
    new_value: bytes,
    proof: list[bytes],
    stored_root: bytes | None,
    witness_address: bytes | None = None,
    witness_counter: int | None = None,
    witness_value: bytes | None = None,
) -> bytes | None:
    """Verify the old-state proof against stored_root and return the candidate
    new root (None if the tree becomes/stays empty). Raises ValueError on a
    proof that does not verify.
    """
    return compute_new_root(
        address,
        old_counter,
        old_value,
        new_counter,
        new_value,
        proof,
        stored_root,
        witness_address=witness_address,
        witness_counter=witness_counter,
        witness_value=witness_value,
    )


def verify_mac(
    mac_key: bytes, wallet_id: bytes, counter: int, root: bytes, mac: bytes
) -> bool:
    """Return True iff `mac` == HMAC(mac_key, wallet_id || counter(4B BE) || root)."""
    expected = _compute_mac(mac_key, wallet_id, counter.to_bytes(4, "big"), root)
    return expected == mac


def queue_put(
    wallet_id: bytes,
    pending_id: int,
    counter: int,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> None:
    """Store an approved edit intent as PENDING under pending_id (pull model)."""
    import storage.ward_store as ward_store

    ward_store.queue_put(wallet_id, pending_id, counter, address, old_value, new_value)


def queue_drop(wallet_id: bytes, pending_id: int) -> None:
    """Clear a pending edit after a successful WARDConfirmedByWM."""
    import storage.ward_store as ward_store

    ward_store.queue_drop(wallet_id, pending_id)


def queue_discard(wallet_id: bytes, pending_id: int) -> None:
    """Discard a pending edit without finalizing (spec-parity alias of queue_drop)."""
    import storage.ward_store as ward_store

    ward_store.queue_drop(wallet_id, pending_id)


async def _resolve_pending_id(wallet_id: bytes, pending_id: int | None) -> int:
    """Resolve which queued candidate an operation targets.

    - pending_id given: use it verbatim (the caller checks the record exists).
    - pending_id omitted: single-slot backward compatibility — if exactly one
      candidate is queued for this wallet, target it; raise if none is queued or
      the choice is ambiguous (more than one candidate in flight).
    """
    if pending_id is not None:
        return pending_id

    import storage.ward_store as ward_store
    from trezor.wire import DataError

    entries = ward_store.queue_list(wallet_id)
    if len(entries) == 1:
        return entries[0][0]
    if not entries:
        raise DataError("no pending candidate")
    raise DataError("pending_id required: multiple candidates queued")


async def discard_pending_impl(
    pending_id: int | None = None,
) -> tuple[bytes | None, bytes]:
    """Abandon queued pending edit(s) without finalizing.

    Wallet-scoped: only candidates belonging to this wallet are touched, so a
    candidate for a different hidden wallet is always left intact.
    - pending_id given: drop just that candidate; returns (its_address, wallet_id),
      or (None, wallet_id) if no such candidate exists for this wallet.
    - pending_id omitted: drop EVERY candidate queued for this wallet; returns
      (None, wallet_id).
    Idempotent in both modes.
    """
    import storage.ward_store as ward_store

    wallet_id = await _get_wallet_id()

    if pending_id is None:
        dropped = ward_store.queue_drop_all(wallet_id)
        if __debug__:
            from trezor import log

            log.debug(
                __name__,
                "discard_pending_impl: dropped %d candidate(s) for wallet_id=%s",
                dropped,
                wallet_id,
            )
        return None, wallet_id

    rec = ward_store.queue_get(wallet_id, pending_id)
    if rec is None:
        return None, wallet_id
    _counter, _state, address, _ov, _nv, _root, _mac = rec
    ward_store.queue_drop(wallet_id, pending_id)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "discard_pending_impl: dropped pending_id=%d for wallet_id=%s",
            pending_id,
            wallet_id,
        )

    return address, wallet_id


async def lookup_label_impl(
    address: bytes, value: bytes, proof: list[bytes], counter: int
) -> bytes | None:
    """On-device label lookup: authenticate (address, value) against the active
    wallet's stored WARD root and return the verified value, or None if it does
    not verify (or the tree is empty). Membership-only (the trust-anchor primitive
    behind Core.lookup_label).
    """
    import storage.ward_session as ward_session

    wallet_id = await _get_wallet_id()
    present, stored_root = ward_session.root_get(wallet_id)
    if not present or stored_root is None:
        return None
    if verify_proof(address, counter, value, proof, stored_root):
        return value
    return None


# ---------------------------------------------------------------------------
# Write / lookup orchestration (formerly inline in the message handlers).
# ---------------------------------------------------------------------------


def _display_bytes(value: bytes) -> str:
    """Best-effort rendering of an arbitrary WARD byte string for a trusted screen:
    UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        from ubinascii import hexlify

        return hexlify(value).decode()


async def _confirm_update(address: bytes, new_value: bytes) -> None:
    """Trusted on-device confirmation of a WARD edit intent. Raises
    ActionCancelled if the user rejects; returns normally on approval."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    if len(new_value) == 0:
        title = "Delete WARD entry"
    else:
        title = "Queue WARD entry"

    # PropertyType is a 3-tuple (name, value, is_data); is_data=True renders the
    # value as monospace data.
    props = [("Key", _display_bytes(address), True)]
    if len(new_value) != 0:
        props.append(("New value", _display_bytes(new_value), True))

    await confirm_properties(
        "ward_update",
        title,
        props,
        hold=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def queue_update_impl(
    address: bytes,
    new_value: bytes,
) -> tuple[int, bytes]:
    """Queue an edit INTENT (pull model). Shows the queued change on a trusted
    screen and, ONLY on user approval, allocates a pending_id and stores the intent
    PENDING. Under the strict counter model the candidate counter is NOT derived
    here: queueing captures user intent only. counter_T is first derived inside the
    WM-synchronized commit flow (WARDPerformUpdate), against the attested round
    state. No proof is taken and the root is NOT computed here either. Returns
    (pending_id, wallet_id). Raises ActionCancelled if the user rejects, DataError
    on invariant violation.
    """
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    # Multi-slot queue: several intents may be in flight per wallet, bounded by the
    # storage cap. Committing stays serialized by counter (see confirmed_by_wm_impl).
    if ward_store.queue_count(wallet_id) >= ward_store.MAX_PENDING:
        raise DataError("pending queue is full for this wallet")

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "queue_update_impl: confirm intent wallet_id=%s address=%s new_value_len=%d",
            wallet_id,
            address,
            len(new_value),
        )

    # Trusted confirmation gates the intent (WP-F5). Raises on user rejection.
    await _confirm_update(address, new_value)

    pending_id = ward_store.queue_alloc_id()
    # counter_T left unset (0) at queue time; derived at WARDPerformUpdate.
    ward_store.queue_put(wallet_id, pending_id, 0, address, b"", new_value)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "queue_update_impl: queued intent wallet_id=%s pending_id=%d",
            wallet_id,
            pending_id,
        )

    return pending_id, wallet_id


async def lookup_impl(
    address: bytes,
    value: bytes | None,
    proof: list[bytes],
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    counter: int | None = None,
    witness_counter: int | None = None,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Verify a membership / non-membership proof against the device's
    authenticated root. Returns (valid, counter, membership, wallet_id, ward_id).
    """
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    membership_query = witness_address is None and value is not None

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()
    present, stored_root = ward_session.root_get(wallet_id)
    if not present:
        raise DataError("no authenticated root in session")

    if stored_root is None:
        # Empty tree: membership trivially false, non-membership trivially true.
        return (
            not membership_query,
            ward_store.get_counter(wallet_id),
            membership_query,
            wallet_id,
            ward_id,
        )

    if not membership_query:
        if witness_value is None or witness_counter is None:
            raise DataError(
                "witness_value and witness_counter required for non-membership proof"
            )
        valid = verify_nonmembership(
            address, witness_address, witness_counter, witness_value, proof, stored_root
        )
        membership = False
    else:
        if counter is None:
            raise DataError("counter required for membership proof")
        valid = verify_proof(address, counter, value, proof, stored_root)
        membership = True

    return valid, ward_store.get_counter(wallet_id), membership, wallet_id, ward_id


async def intent_address_impl(pending_id: int | None) -> tuple[int, bytes]:
    """Resolve pending_id to (resolved_pending_id, address) for the active wallet.
    The Core gateway calls this to build the WARDProofRequest (naming the address
    and the pending_id) before pulling the proof for WARDPerformUpdate."""
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)
    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, address, _ov, _nv, _root, _mac = rec

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "intent_address_impl: wallet_id=%s pending_id=%d address=%s",
            wallet_id,
            pid,
            address,
        )

    return pid, address


async def perform_update_impl(
    pending_id: int | None,
    value: bytes | None,
    proof: list[bytes],
    counter: int | None,
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    witness_counter: int | None = None,
) -> tuple[int, bytes | None, bytes | None, bytes, bytes]:
    """Authorize a queued intent using a proof the device PULLED on demand.

    The proof package (value/counter for membership, witness_* for non-membership,
    empty for an empty tree) is the authoritative current state. This is where the
    candidate counter is FIRST derived under the strict model: the device is the
    counter authority and sets counter_T = current authenticated counter + 1 here,
    inside the WM-synchronized flow -- never at queue time and never from host/app
    input. Verifies the proof against the stored root, computes (root_T, mac_T) for
    counter_T, persists counter_T, and marks the intent COMMITTED. The durable
    counter floor is NOT advanced (that happens at confirm). pending_id selects the
    intent; if omitted, falls back to the single queued one. Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id).
    """
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)

    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, _address, _old_value, new_value, _root, _mac = rec

    # Strict model: derive the candidate counter now, from the device's current
    # authenticated floor -- not from the (unset) queue-time value.
    counter_t = ward_store.get_counter(wallet_id) + 1

    present, stored_root = ward_session.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT: treat "no root in session" as an authenticated empty
        # tree only when the durable counter floor is still zero.
        if ward_store.get_counter(wallet_id) == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    # Membership -> value + counter (UPDATE/DELETE); non-membership -> witness_*
    # (INSERT); empty tree -> no proof (INIT). compute_new_root keys INSERT/INIT off
    # an empty old_value, so map an absent pulled value to b"".
    old_value = value if value is not None else b""
    old_counter = counter if counter is not None else 0

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "perform_update_impl: verify pending_id=%d wallet_id=%s counter_T=%d proof_len=%d old_counter=%d witness=%s",
            pid,
            wallet_id,
            counter_t,
            len(proof),
            old_counter,
            "yes" if witness_address is not None else "no",
        )

    try:
        root_t = compute_new_root(
            _address,
            old_counter,
            old_value,
            counter_t,
            new_value,
            proof,
            stored_root,
            witness_address=witness_address,
            witness_counter=witness_counter,
            witness_value=witness_value,
        )
    except ValueError as e:
        raise DataError(str(e))

    # Candidate MAC binds wallet_id and counter_T to root_T.
    if root_t is not None:
        mac_key = await _derive_mac_key(b"root_mac")
        mac_t = _compute_mac(mac_key, wallet_id, counter_t.to_bytes(4, "big"), root_t)
    else:
        mac_t = None

    # Persist the just-derived counter_T alongside the computed (root_T, mac_T).
    ward_store.queue_set_computed(wallet_id, pid, counter_t, root_t, mac_t)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "perform_update_impl: computed candidate wallet_id=%s pending_id=%d counter_T=%d root_T=%s",
            wallet_id,
            pid,
            counter_t,
            "EMPTY" if root_t is None else "set",
        )

    ward_id = await _get_ward_id()
    return counter_t, root_t, mac_t, wallet_id, ward_id


async def confirmed_by_wm_impl(
    counter_msg: int,
    mac_msg: bytes | None,
    wm_signature: bytes,
    pending_id: int | None = None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """Verify the WM final attestation over the COMMITTED candidate, then install
    (root_T, counter_T), advance the counter + QM ceiling, and drop that candidate
    from the queue. The only step that advances the device counter. pending_id
    selects the candidate; if omitted, falls back to the single queued candidate.
    Returns (counter, new_root, wallet_id, root_mac).

    Note: under the strict model counter_T is derived at WARDPerformUpdate, not at
    queue time. With several intents performed, each was stamped counter_T = base +
    1 from the floor current at its perform. Confirming one advances counter_loc, so
    any sibling still stamped at the same counter becomes stale and is rejected here
    by the anti-rollback check below — it must be re-performed (or discarded).
    Commit stays serialized by counter even though queueing is not. The device is
    the counter authority; the WM only co-signs the exact (counter_T, mac_T) the
    device derived.
    """
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)

    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no candidate to finalize")
    counter, state, _address, _old_value, _new_value, root, mac = rec

    if state != ward_store.QUEUE_COMMITTED:
        raise DataError("candidate has not been performed")

    # The candidate MAC (all-zero when the tree becomes empty) is what the WM signs.
    candidate_mac = mac if mac is not None else _ZERO_MAC
    msg_mac = mac_msg if mac_msg is not None else _ZERO_MAC

    if counter_msg != counter or msg_mac != candidate_mac:
        raise DataError("confirmation does not match the committed candidate")

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "confirmed_by_wm_impl: verify pending_id=%d wallet_id=%s counter_msg=%d mac_present=%s",
            pid,
            wallet_id,
            counter_msg,
            "yes" if mac_msg is not None else "no",
        )

    ward_id = await _get_ward_id()
    if not verify_ward_final(ward_id, counter, candidate_mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    # Anti-rollback: the finalized counter must exceed the durable local floor.
    if counter <= ward_store.get_counter(wallet_id):
        raise DataError("counter_T is not ahead of counter_loc")

    # Install the volatile authenticated root and persist only counter_loc.
    import storage.ward_session as ward_session

    ward_session.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter)
    ward_store.queue_drop(wallet_id, pid)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "confirmed_by_wm_impl: installed wallet_id=%s counter=%d root=%s",
            wallet_id,
            counter,
            "EMPTY" if root is None else "set",
        )

    return counter, root, wallet_id, mac


async def sync_impl() -> tuple[bytes, int, bytes, bytes]:
    """Begin a sync round: mint a fresh per-round nonce (anti-replay) and store it.
    Also derives and returns the WM-facing ward_id so the host can address the WM
    for this round without inventing it. Returns (nonce, version, wallet_id,
    ward_id)."""
    import storage.ward_session as ward_session
    from trezor.crypto import random

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()
    nonce = random.bytes(ward_session.NONCE_LENGTH)
    ward_session.sync_begin(wallet_id, nonce)

    if __debug__:
        from trezor import log

        log.debug(__name__, "sync_impl: minted nonce for wallet_id=%s", wallet_id)

    return nonce, _WARD_VERSION, wallet_id, ward_id


async def ingest_attestation_impl(
    counter: int, mac_msg: bytes | None, wm_signature: bytes
) -> tuple[int, bytes]:
    """Verify + record the WM freshness attestation for the open sync round.
    Returns (counter, wallet_id)."""
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    import storage.ward_session as ward_session
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    ctx = ward_session.sync_get(wallet_id)
    if ctx is None:
        raise DataError("no sync round in progress")
    nonce, _state, _counter, _mac = ctx

    ward_id = await _get_ward_id()
    mac = mac_msg if mac_msg is not None else _ZERO_MAC
    if not verify_wm_attestation(ward_id, nonce, counter, mac, wm_signature):
        raise DataError("WM attestation verification failed")

    # Anti-rollback: the attested counter cannot precede the device's floor.
    if counter < ward_store.get_counter(wallet_id):
        raise DataError("attested counter is older than counter_loc")

    ward_session.sync_set_attested(wallet_id, counter, mac_msg)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "ingest_attestation_impl: accepted counter=%d for wallet_id=%s",
            counter,
            wallet_id,
        )

    return counter, wallet_id


async def reconcile_impl(
    root: bytes | None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """Adopt the host-supplied root after binding it to the attested mac_ext,
    install (root, counter_ext), advance the ceiling, and clear the round.
    Adopt-only (pending edits go through the write path). Returns
    (counter, new_root, wallet_id, root_mac)."""
    import storage.ward_store as ward_store
    import storage.ward_session as ward_session
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    ctx = ward_session.sync_get(wallet_id)
    if ctx is None or ctx[1] != ward_session.SYNC_ATTESTED:
        raise DataError("no attested sync round to merge")
    _nonce, _state, counter_ext, mac_ext = ctx

    if mac_ext is None:
        # Attested empty tree: the supplied root must be absent too.
        if root is not None:
            raise DataError("attested tree is empty but a root was supplied")
    else:
        if root is None:
            raise DataError("attested tree is non-empty but no root was supplied")
        if len(root) != ward_store.ROOT_LENGTH:
            raise DataError("root must be exactly 32 bytes")
        mac_key = await _derive_mac_key(b"root_mac")
        computed = _compute_mac(mac_key, wallet_id, counter_ext.to_bytes(4, "big"), root)
        if computed != mac_ext:
            raise DataError("root does not match the attested mac")

    ward_session.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter_ext)
    ward_session.sync_clear()

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "reconcile_impl: adopted counter=%d root=%s wallet_id=%s",
            counter_ext,
            "EMPTY" if root is None else "set",
            wallet_id,
        )

    return counter_ext, root, wallet_id, mac_ext


async def list_pending_impl() -> tuple[list[int], list[bytes], bytes, bytes]:
    """Return (pending_ids, addresses, wallet_id, ward_id) for every queued
    candidate of the active wallet, in allocation order (the two lists are
    parallel). ward_id lets a host resolve the WM-facing anchor up front."""
    import storage.ward_store as ward_store

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()

    pending_ids = []  # type: list[int]
    addresses = []  # type: list[bytes]
    for pid, address in ward_store.queue_list(wallet_id):
        pending_ids.append(pid)
        addresses.append(address)

    return pending_ids, addresses, wallet_id, ward_id


async def debug_set_root_impl(
    root: bytes,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """DEBUG-ONLY unauthenticated root injection (seed a root in one call). Installs
    the root, increments the counter by 1. Rejected on production firmware. Returns
    (counter, new_root, wallet_id, root_mac)."""
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if not __debug__:
        raise DataError("WARDDebugSetRoot is only accepted in debug builds")

    if len(root) != ward_store.ROOT_LENGTH:
        raise DataError("root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()
    counter = ward_store.bump_counter(wallet_id)
    ward_session.root_set(wallet_id, root)

    mac_key = await _derive_mac_key(b"root_mac")
    new_root = root
    root_mac = (
        _compute_mac(mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )

    return counter, new_root, wallet_id, root_mac
