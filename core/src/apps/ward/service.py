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
#   - final/commit (WARDConfirmCommit):
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
    wallet_id: bytes, nonce: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's freshness attestation for a sync round:

        b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + wallet_id
        + counter.to_bytes(4, "big")
        + mac
    )
    return _verify(message, signature)


def verify_ward_final(
    wallet_id: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's final attestation over the committed WARD candidate:

        b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac
    """
    message = _WARD_FINAL_DOMAIN + wallet_id + counter.to_bytes(4, "big") + mac
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
    counter: int,
    root: bytes | None,
    mac: bytes | None,
    address: bytes,
) -> None:
    """Store the verified candidate as the PENDING edit for wallet_id."""
    import storage.ward_store as ward_store

    ward_store.queue_put(wallet_id, counter, root, mac, address)


def queue_drop() -> None:
    """Clear the pending edit after a successful WARDConfirmCommit."""
    import storage.ward_store as ward_store

    ward_store.queue_drop()


def queue_discard() -> None:
    """Discard the pending edit without finalizing (spec-parity alias of queue_drop)."""
    import storage.ward_store as ward_store

    ward_store.queue_drop()


async def discard_pending_impl() -> tuple[bytes | None, bytes]:
    """Abandon the current wallet's queued pending edit without finalizing it.

    Wallet-scoped: only drops the candidate if it belongs to this wallet (the
    single queue slot is checked via queue_get before deleting, so a candidate for
    a different hidden wallet is left intact). Idempotent: returns
    (None, wallet_id) when nothing is queued for this wallet. Returns
    (discarded_address, wallet_id) otherwise.
    """
    import storage.ward_store as ward_store

    wallet_id = await _get_wallet_id()

    rec = ward_store.queue_get(wallet_id)
    if rec is None:
        return None, wallet_id
    _counter, _root, _mac, _state, address = rec
    ward_store.queue_drop()

    if __debug__:
        from trezor import log

        log.debug(
            __name__, "discard_pending_impl: dropped candidate for wallet_id=%s", wallet_id
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


async def add_pending_impl(
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    new_counter: int,
    proof: list[bytes],
    old_counter: int | None = None,
    witness_address: bytes | None = None,
    witness_counter: int | None = None,
    witness_value: bytes | None = None,
) -> tuple[int, bytes]:
    """Verify a leaf change against the stored root and queue it PENDING.

    Computes the candidate root + MAC, stamps the changed leaf with new_counter
    (== current root counter + 1), stores the candidate WITHOUT advancing the
    counter (the counter only moves at WARDConfirmCommit). Returns
    (candidate_counter, wallet_id). Raises DataError on any invariant violation.
    """
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    # Depth-1 offline queue: only one uncommitted candidate per wallet in flight.
    if ward_store.queue_get(wallet_id) is not None:
        raise DataError("a pending candidate already exists for this wallet")

    # Candidate counter must be exactly current root counter + 1 (anti-rollback).
    current_counter = ward_store.get_counter(wallet_id)
    if new_counter != current_counter + 1:
        raise DataError("new_counter must equal current global counter + 1")

    oc = old_counter if old_counter else 0
    present, stored_root = ward_session.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT is allowed before an explicit bootstrap round:
        # treat "no root in session" as an authenticated empty tree only when
        # the durable counter floor is still zero. Non-empty wallets must sync
        # first so edits are anchored to an authenticated root.
        if current_counter == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    try:
        root_t = compute_new_root(
            address,
            oc,
            old_value,
            new_counter,
            new_value,
            proof,
            stored_root,
            witness_address=witness_address,
            witness_counter=witness_counter,
            witness_value=witness_value,
        )
    except ValueError as e:
        raise DataError(str(e))

    # Candidate MAC binds wallet_id and the candidate counter to root_T.
    if root_t is not None:
        mac_key = await _derive_mac_key(b"root_mac")
        mac_t = _compute_mac(mac_key, wallet_id, new_counter.to_bytes(4, "big"), root_t)
    else:
        mac_t = None

    # TODO: show address + old_value -> new_value confirmation dialog when UI ready.

    ward_store.queue_put(wallet_id, new_counter, root_t, mac_t, address)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "add_pending_impl: queued candidate wallet_id=%s counter_T=%d root_T=%s",
            wallet_id,
            new_counter,
            "EMPTY" if root_t is None else "set",
        )

    return new_counter, wallet_id


async def lookup_impl(
    address: bytes,
    value: bytes | None,
    proof: list[bytes],
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    counter: int | None = None,
    witness_counter: int | None = None,
) -> tuple[bool, int, bool, bytes]:
    """Verify a membership / non-membership proof against the device's
    authenticated root. Returns (valid, counter, membership, wallet_id).
    """
    import storage.ward_session as ward_session
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    membership_query = witness_address is None and value is not None

    wallet_id = await _get_wallet_id()
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

    return valid, ward_store.get_counter(wallet_id), membership, wallet_id


async def commit_impl() -> tuple[int, bytes | None, bytes | None, bytes]:
    """Emit the queued PENDING candidate and mark it COMMITTED. The counter is
    NOT advanced (that happens at confirm). Returns (counter, root, mac, wallet_id).
    """
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    rec = ward_store.queue_get(wallet_id)
    if rec is None:
        raise DataError("no pending candidate to commit")
    counter, root, mac, _state, _address = rec

    ward_store.queue_set_committed(wallet_id)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "commit_impl: emit candidate wallet_id=%s counter_T=%d root_T=%s",
            wallet_id,
            counter,
            "EMPTY" if root is None else "set",
        )

    return counter, root, mac, wallet_id


async def confirm_commit_impl(
    counter_msg: int, mac_msg: bytes | None, qm_signature: bytes
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """Verify the WM final attestation over the committed candidate, then install
    (root_T, counter_T), advance the counter + QM ceiling, and drop the queue.
    The only step that advances the device counter. Returns
    (counter, new_root, wallet_id, root_mac).
    """
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    rec = ward_store.queue_get(wallet_id)
    if rec is None:
        raise DataError("no candidate to finalize")
    counter, root, mac, state, _address = rec

    if state != ward_store.QUEUE_COMMITTED:
        raise DataError("candidate has not been committed")

    # The candidate MAC (all-zero when the tree becomes empty) is what the WM signs.
    candidate_mac = mac if mac is not None else _ZERO_MAC
    msg_mac = mac_msg if mac_msg is not None else _ZERO_MAC

    if counter_msg != counter or msg_mac != candidate_mac:
        raise DataError("finalize does not match the committed candidate")

    if not verify_ward_final(wallet_id, counter, candidate_mac, qm_signature):
        raise DataError("WM final attestation verification failed")

    # Anti-rollback: the finalized counter must exceed the durable local floor.
    if counter <= ward_store.get_counter(wallet_id):
        raise DataError("counter_T is not ahead of counter_loc")

    # Install the volatile authenticated root and persist only counter_loc.
    import storage.ward_session as ward_session

    ward_session.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter)
    ward_store.queue_drop()

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "confirm_commit_impl: installed wallet_id=%s counter=%d root=%s",
            wallet_id,
            counter,
            "EMPTY" if root is None else "set",
        )

    return counter, root, wallet_id, mac


async def sync_impl() -> tuple[bytes, int, bytes]:
    """Begin a sync round: mint a fresh per-round nonce (anti-replay) and store it.
    Returns (nonce, version, wallet_id)."""
    import storage.ward_session as ward_session
    from trezor.crypto import random

    wallet_id = await _get_wallet_id()
    nonce = random.bytes(ward_session.NONCE_LENGTH)
    ward_session.sync_begin(wallet_id, nonce)

    if __debug__:
        from trezor import log

        log.debug(__name__, "sync_impl: minted nonce for wallet_id=%s", wallet_id)

    return nonce, _WARD_VERSION, wallet_id


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

    mac = mac_msg if mac_msg is not None else _ZERO_MAC
    if not verify_wm_attestation(wallet_id, nonce, counter, mac, wm_signature):
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


async def list_pending_impl() -> tuple[list[bytes], bytes]:
    """Return (pending_edit_addresses, wallet_id). MVP queue depth 1 → 0 or 1 addr."""
    import storage.ward_store as ward_store

    wallet_id = await _get_wallet_id()

    addresses = []
    rec = ward_store.queue_get(wallet_id)
    if rec is not None:
        _counter, _root, _mac, _state, address = rec
        addresses.append(address)

    return addresses, wallet_id


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
