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
_ZERO_PUBKEY = b"\x00" * 32  # the "unprovisioned" placeholder value; never verify against it
_ZERO_SIG = b"\x00" * 64  # a degenerate signature that must never be accepted (see _verify)

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
#   entry_key  = sha256(app_id || 0x00 || type || 0x00 || identifier)   (== trie path)
#   value_hash = sha256(counter(4B BE) || value)
#   leaf_hash  = sha256(0x00 || entry_key || value_hash)
#
# The counter is the GLOBAL root counter stamped onto the leaf on change; it lives
# inside value_hash (never in entry_key, so an entry keeps one stable path across
# versions). compute_new_root() is the single INIT/INSERT/UPDATE/DELETE state
# machine; it does not enforce the per-generation +1 rule -- update_entry() does.
# ---------------------------------------------------------------------------


def sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


# MVP entry type: the only kind of identifier keyed today is an address. It is
# baked into entry_key so the key layout reserves a type slot, but it is a constant
# (no wire/storage field). Later kinds add real types by varying this argument.
_ENTRY_TYPE_ADDRESS = "address"


def entry_key(
    k_index: bytes,
    app_id,
    identifier: bytes,
    key_type: str = _ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """Keyed 32-byte trie path (ward-design.md §1/§3):

        scope     = app_id || 0x00 || key_type || 0x00 || device_id(1B)
        entry_key = HMAC-SHA256(K_index, scope || identifier)

    A PRF-derived path, NOT an authenticator (§2.5): only a holder of K_index can
    compute it, so the host cannot forge a path or brute-force a low-entropy
    identifier. `device_id`=0 is a global entry; >0 is a device slot (§5). Must stay
    byte-for-byte identical to trezorlib `ward_crypto.entry_key` and the host."""
    from trezor.crypto import hmac as crypto_hmac

    if app_id is None:
        app_id = b""
    elif isinstance(app_id, str):
        app_id = app_id.encode()
    scope = app_id + b"\x00" + key_type.encode() + b"\x00" + bytes([device_id & 0xFF])
    return crypto_hmac(crypto_hmac.SHA256, k_index, scope + identifier).digest()


def commit_of(nonce: bytes, tag: bytes, ct: bytes) -> bytes:
    """Keyless leaf-value commitment: sha256(0x02 || nonce || tag || len32(ct) || ct)
    (§2.2). A host with no keys can still recompute it. len(ct)==0 is a delete."""
    return sha256d(b"\x02" + nonce + tag + len(ct).to_bytes(4, "big") + ct)


def leaf_hash_of(entry_key_: bytes, commit: bytes) -> bytes:
    """Leaf: sha256(0x00 || entry_key || commit) (§2.2). Takes the commitment
    directly, so a verifier can rebuild a witness leaf from (entry_key, commit)."""
    return sha256d(b"\x00" + entry_key_ + commit)


def leaf_hash(entry_key_: bytes, nonce: bytes, tag: bytes, ct: bytes) -> bytes:
    """Leaf hash from the encrypted blob: leaf_hash_of(entry_key, commit_of(...))."""
    return leaf_hash_of(entry_key_, commit_of(nonce, tag, ct))


# --- leaf value codec (ChaCha20-Poly1305 RFC-7539, 12-byte nonce, §2.1) ---

_AEAD_BUCKETS = (64, 256, 1024, 4096)


def _aead_aad(entry_key_: bytes, entry_type: str) -> bytes:
    return b"\x02" + entry_key_ + entry_type.encode()


def _pad_bucket(pt: bytes) -> bytes:
    for b in _AEAD_BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    rem = (-len(pt)) % _AEAD_BUCKETS[-1]
    return pt + b"\x00" * rem


def encrypt_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: str,
    c_leaf: int,
    identifier: bytes,
    value: bytes,
) -> tuple:
    """Return (nonce, tag, ct). nonce is fresh-random per write (§4.5)."""
    from trezor.crypto import chacha20poly1305_encrypt, random

    nonce = random.bytes(12)
    pt = _pad_bucket(
        c_leaf.to_bytes(4, "big")
        + len(identifier).to_bytes(2, "big")
        + identifier
        + len(value).to_bytes(4, "big")
        + value
    )
    cipher = chacha20poly1305_encrypt(k_data, nonce)
    cipher.auth(_aead_aad(entry_key_, entry_type))
    ct = cipher.encrypt(pt)
    tag = cipher.finish()
    return nonce, tag, ct


def decrypt_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: str,
    nonce: bytes,
    tag: bytes,
    ct: bytes,
) -> tuple:
    """Return (c_leaf, identifier, value). Raises on tag mismatch (hard abort, §3.1)."""
    from trezor.crypto import AuthenticationError, chacha20poly1305_decrypt

    cipher = chacha20poly1305_decrypt(k_data, nonce)
    cipher.auth(_aead_aad(entry_key_, entry_type))
    pt = cipher.decrypt(ct)
    try:
        cipher.finish(tag)
    except AuthenticationError:
        raise ValueError("WARD leaf AEAD tag mismatch")
    c_leaf = int.from_bytes(pt[0:4], "big")
    id_len = int.from_bytes(pt[4:6], "big")
    off = 6 + id_len
    identifier = pt[6:off]
    val_len = int.from_bytes(pt[off : off + 4], "big")
    off += 4
    value = pt[off : off + val_len]
    return c_leaf, identifier, value


def addr_bit(entry_key_: bytes, bit: int) -> int:
    return (entry_key_[bit // 8] >> (7 - (bit % 8))) & 1


def internal_hash(left: bytes, right: bytes) -> bytes:
    return sha256d(b"\x01" + left + right)


def reconstruct(start_hash: bytes, proof: list, entry_key_: bytes) -> bytes:
    """Walk proof from leaf toward root, rebuilding hashes. entry_key_ is the 32-byte
    trie path of the leaf the walk starts from."""
    node = start_hash
    for elem in proof:
        bit = elem[0]
        sibling = bytes(elem[1:])
        if addr_bit(entry_key_, bit) == 0:
            node = internal_hash(node, sibling)
        else:
            node = internal_hash(sibling, node)
    return node


def verify_proof(
    entry_key_: bytes,
    nonce: bytes,
    tag: bytes,
    ct: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify an MPT membership proof for the leaf blob (nonce, tag, ct) at
    entry_key against expected_root. The device forms the leaf from the encrypted
    blob (commit -> leaf) it holds."""
    node = leaf_hash(entry_key_, nonce, tag, ct)
    node = reconstruct(node, proof, entry_key_)
    return node == expected_root


def verify_nonmembership(
    entry_key_: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify that entry_key is NOT in the tree.

    The witness leaf is supplied as two hashes -- (witness_entry_key,
    witness_commit) -- that occupies entry_key's path, revealing nothing about the
    witness's plaintext identifier or value. We verify: (1) the witness leaf
    rebuilt from the two hashes is in the tree; (2) witness_entry_key != entry_key;
    (3) both share the same bit at every proof position (closest leaf)."""
    if witness_entry_key == entry_key_:
        return False

    for elem in proof:
        bit = elem[0]
        if addr_bit(entry_key_, bit) != addr_bit(witness_entry_key, bit):
            return False

    witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
    return reconstruct(witness_leaf, proof, witness_entry_key) == expected_root


def compute_new_root(
    entry_key_: bytes,
    old_leaf,
    new_leaf,
    proof: list,
    stored_root,
    witness_entry_key=None,
    witness_commit=None,
):
    """Verify the old state (old_leaf, proof) against stored_root, then compute the
    new root. `old_leaf`/`new_leaf` are (nonce, tag, ct) tuples the device produced,
    or None: old_leaf=None => INSERT, new_leaf=None => DELETE. Returns the new root
    (None if the tree becomes/stays empty), or raises ValueError if the old-state
    proof does not verify. INSERT's witness neighbour may belong to another app, so
    it is supplied privacy-preservingly as (witness_entry_key, witness_commit)."""
    inserting = old_leaf is None
    deleting = new_leaf is None
    if inserting and deleting:
        raise ValueError("old_leaf and new_leaf cannot both be empty")

    if inserting:
        if len(proof) == 0 and witness_entry_key is None:
            # INIT: tree was empty
            if stored_root is not None:
                raise ValueError("Tree is not empty; supply non-membership proof")
            return leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])

        if witness_entry_key is None or witness_commit is None:
            raise ValueError("witness_entry_key/witness_commit required for INSERT")
        if witness_entry_key == entry_key_:
            raise ValueError("witness_entry_key must differ from entry_key")

        for elem in proof:
            bit = elem[0]
            if addr_bit(entry_key_, bit) != addr_bit(witness_entry_key, bit):
                raise ValueError("Witness does not occupy target's path")

        witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
        witness_in_tree = reconstruct(witness_leaf, proof, witness_entry_key)
        if witness_in_tree != stored_root:
            raise ValueError("Non-membership proof invalid: witness not in tree")

        split_bit = None
        for b in range(256):
            if addr_bit(entry_key_, b) != addr_bit(witness_entry_key, b):
                split_bit = b
                break
        if split_bit is None:
            raise ValueError("entry_key and witness_entry_key are equal")

        new_leaf_t = leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])
        if addr_bit(entry_key_, split_bit) == 0:
            new_branch = internal_hash(new_leaf_t, witness_leaf)
        else:
            new_branch = internal_hash(witness_leaf, new_leaf_t)
        return reconstruct(new_branch, proof, witness_entry_key)

    if deleting:
        if stored_root is None:
            raise ValueError("No Merkle root stored on device")
        current_leaf = leaf_hash(entry_key_, old_leaf[0], old_leaf[1], old_leaf[2])
        if reconstruct(current_leaf, proof, entry_key_) != stored_root:
            raise ValueError("Old value proof invalid")
        if len(proof) == 0:
            return None
        sibling_hash = bytes(proof[0][1:])
        return reconstruct(sibling_hash, proof[1:], entry_key_)

    # UPDATE
    if stored_root is None:
        raise ValueError("No Merkle root stored on device")
    current_leaf = leaf_hash(entry_key_, old_leaf[0], old_leaf[1], old_leaf[2])
    if reconstruct(current_leaf, proof, entry_key_) != stored_root:
        raise ValueError("Old value proof invalid")
    new_leaf_h = leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])
    return reconstruct(new_leaf_h, proof, entry_key_)


def _multiproof_root(items, stored_root):
    """Recompute the trie root over a set of UPDATE items against `stored_root`, and
    return the new root, via a shape-preserving Merkle multiproof (§4.2).

    Each item is `(entry_key, old_leaf_hash, new_leaf_hash, proof)` where `proof` is
    the membership proof (bit, sibling) leaf→root of the OLD leaf against
    `stored_root`. All items must be UPDATES of leaves that already exist, so the
    trie SHAPE is unchanged and only leaf hashes move — the shared structure of the k
    proof paths is overlaid into one partial tree, external (boundary) siblings come
    from the proofs, and internal nodes shared by two batch leaves are recomputed from
    their children (never from a now-stale proof sibling).

    Crucially this uses proofs against the SINGLE common `stored_root` (exactly what
    the host serves for the whole batch), not per-leaf running roots. It VERIFIES by
    recomputing the old root from the overlay and requiring it to equal `stored_root`,
    then returns the new root with the new leaf hashes substituted. Raises ValueError
    on any inconsistency (mismatched branch bit / sibling / root)."""
    # Partial tree keyed by path = tuple of (bit, dir) taken from the root.
    branch = {}  # path -> branch_bit
    occupied = set()  # paths on some item's root→leaf walk (real nodes)
    old_leaf = {}  # path -> old leaf hash
    new_leaf = {}  # path -> new leaf hash
    sib_seen = {}  # path -> list of boundary sibling hashes recorded for it

    for ek, oh, nh, proof in items:
        path = ()
        occupied.add(path)
        for elem in reversed(proof):  # root → leaf order
            b = elem[0]
            sib = bytes(elem[1:])
            d = addr_bit(ek, b)
            if path in branch:
                if branch[path] != b:
                    raise ValueError("inconsistent branch bit in batch multiproof")
            else:
                branch[path] = b
            sib_path = path + ((b, 1 - d),)
            sib_seen.setdefault(sib_path, []).append(sib)
            path = path + ((b, d),)
            occupied.add(path)
        old_leaf[path] = oh
        new_leaf[path] = nh

    # A non-occupied sibling is an EXTERNAL subtree: every proof that named it must
    # agree on its hash (this is the cross-proof consistency / verification step).
    for sib_path, sibs in sib_seen.items():
        if sib_path in occupied:
            continue
        for s in sibs:
            if s != sibs[0]:
                raise ValueError("inconsistent boundary sibling in batch multiproof")

    def child_hash(path, leaf_map):
        if path in occupied:
            return node_hash(path, leaf_map)
        sibs = sib_seen.get(path)
        if not sibs:
            raise ValueError("missing sibling in batch multiproof")
        return sibs[0]

    def node_hash(path, leaf_map):
        if path in leaf_map:
            return leaf_map[path]
        if path in branch:
            b = branch[path]
            left = child_hash(path + ((b, 0),), leaf_map)
            right = child_hash(path + ((b, 1),), leaf_map)
            return internal_hash(left, right)
        raise ValueError("dangling node in batch multiproof")

    if node_hash((), old_leaf) != stored_root:
        raise ValueError("batch pre-state proofs do not reconstruct the stored root")
    return node_hash((), new_leaf)


def compute_batch_root(stored_root, ops):
    """Apply a batch of leaf changes to `stored_root` and return the new root (`None`
    if the tree ends empty). Rejects a duplicate `entry_key` within the batch (§4.2).

    Each op is a 6-tuple `(entry_key, old_leaf, new_leaf, proof, witness_entry_key,
    witness_commit)` with the same semantics as `compute_new_root` (old_leaf=None =>
    INSERT, new_leaf=None => DELETE), and `proof` is the pre-state proof against
    `stored_root` (the single common base the host serves for the whole batch).

    - A single-op batch (n=1) delegates to the audited `compute_new_root`, so INIT /
      INSERT / UPDATE / DELETE all keep full generality.
    - A multi-op batch (n>1) currently supports **UPDATES only** (the trie shape is
      unchanged) and is folded by a shape-preserving multiproof (`_multiproof_root`)
      over the common `stored_root` — NOT a sequential running-root apply, which would
      wrongly reject leaf k's `stored_root`-proof. Insert/delete inside a multi-leaf
      batch is rejected here; use single-leaf commits for those until the general
      (shape-changing) multiproof lands.

    Per-leaf counter monotonicity (`C_new > C_old`, §4.5/F12) is enforced by the
    caller (`perform_batch`), not here."""
    seen = []
    for op in ops:
        ek = op[0]
        for prev in seen:
            if prev == ek:
                raise ValueError("duplicate entry_key in batch")
        seen.append(ek)

    if len(ops) == 1:
        op = ops[0]
        return compute_new_root(
            op[0], op[1], op[2], op[3], stored_root,
            witness_entry_key=op[4], witness_commit=op[5],
        )

    items = []
    for ek, old_leaf, new_leaf, proof, w_ek, w_commit in ops:
        if old_leaf is None or new_leaf is None or w_ek is not None:
            raise ValueError(
                "multi-leaf batch supports UPDATES only; use single-leaf commits "
                "for insert/delete"
            )
        items.append(
            (
                ek,
                leaf_hash(ek, old_leaf[0], old_leaf[1], old_leaf[2]),
                leaf_hash(ek, new_leaf[0], new_leaf[1], new_leaf[2]),
                proof,
            )
        )
    if stored_root is None:
        raise ValueError("multi-leaf update batch requires a non-empty tree")
    return _multiproof_root(items, stored_root)


# ---------------------------------------------------------------------------
# WM attestation verification (formerly apps.authdb._qm).
# ---------------------------------------------------------------------------


def _verify(message: bytes, signature: bytes) -> bool:
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    # SECURITY: an all-zero signature must NEVER verify. Combined with an
    # unprovisioned all-zero _WM_PUBKEY it is a degenerate Ed25519 acceptance
    # (R=0, S=0 satisfies [S]B = R + [k]A against the identity/low-order public key),
    # which would let anyone forge a WM attestation with a zero signature. Reject it
    # explicitly, and never attempt verification against the all-zero placeholder
    # key itself (it means "no WM key provisioned yet" -> reject, not "accept").
    if signature == _ZERO_SIG:
        return False
    if _WM_PUBKEY != _ZERO_PUBKEY and ed25519.verify(_WM_PUBKEY, signature, message):
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


async def _derive_k_index() -> bytes:
    """K_index = SLIP21(seed, [b"ward", b"K_index"]).key() -- the HMAC key that
    derives every entry_key path (§1). Seed-scoped and shared across the wallet's
    devices; the per-device axis lives in the entry_key scope, not the key."""
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"ward", b"K_index"])
    return node.key()


async def _derive_k_data(key_type: str) -> bytes:
    """K_data(key_type) = SLIP21(seed, [b"ward", b"K_data", key_type]).key() -- a
    separate AEAD key per entry type (§1), so a PUSH export can hand a host only the
    types it may decrypt. Must match trezorlib ward_crypto.derive_k_data."""
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"ward", b"K_data", key_type.encode()])
    return node.key()


async def entry_key_for(
    app_id, identifier: bytes, key_type: str = _ENTRY_TYPE_ADDRESS, device_id: int = 0
) -> bytes:
    """Compute the opaque entry_key path for (app_id, identifier) under the active
    wallet's K_index. Used by the Core gateway to build a WARDProofRequest without
    leaking the identifier to the host."""
    k_index = await _derive_k_index()
    return entry_key(k_index, app_id, identifier, key_type, device_id)


async def _confirm_export_keys(key_type: str) -> None:
    """Trusted confirmation before handing WARD keys to the host (PUSH). Exporting
    K_index + K_data(key_type) lets the host compute paths and decrypt values for
    this entry type -- a deliberate, user-approved downgrade of the "host holds no
    keys" property. Raises ActionCancelled if the user rejects."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "ward_export_keys",
        "Share WARD keys",
        [
            ("Give this app the ability to read your", key_type, False),
            ("entries?", "The app will be able to compute and decrypt them.", False),
        ],
        hold=True,
        br_code=ButtonRequestType.ProtectCall,
    )


async def export_keys(key_type: str = _ENTRY_TYPE_ADDRESS) -> tuple:
    """PUSH key export: after user confirmation, return (K_index, K_data(key_type)).
    K_sig is never exported. Per-type K_data means the host only gains the ability to
    read the requested entry type. Returns (k_index, k_data)."""
    await _confirm_export_keys(key_type)
    k_index = await _derive_k_index()
    k_data = await _derive_k_data(key_type)
    return k_index, k_data


def _compute_mac(key: bytes, *parts: bytes) -> bytes:
    """HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()


# ---------------------------------------------------------------------------
# Batch-transition authentication (WARD batch-update).
#
# A batch commits N queued intents as ONE root transition (from_root -> to_root,
# counter += 1 for the whole batch -- the counter is a transition/head-generation
# counter, so a batch of any size and a rollback are each a uniform +1; every leaf in
# a batch shares C_leaf = to_counter). Two symmetric MACs authenticate it (MANDATORY):
#   head_mac   = MAC(K_head, TAG_HEAD   || ward_id || counter || root)
#   AuthCommit = MAC(K_auth, TAG_COMMIT || ward_id || from_c || from_root || to_c || to_root)
#   AuthRevert = MAC(K_auth, TAG_REVERT || ward_id || from_c || from_root || to_c || to_root)
# Plus a CONFIG-GATED Ed25519 signature over the AuthCommit preimage, so a hardened
# WM can pre-filter unauthorized transitions and we can benchmark MAC-only vs
# MAC+signature (WARD_KSIG):
#   SigCommit  = Ed25519(K_sig, <same preimage as AuthCommit>)
#
# K_head/K_auth/K_sig are SLIP-21 under m/"ward" (seed-scoped, shared across the
# wallet's devices, like K_index/K_data); the wallet binding is `ward_id` inside
# every preimage. Domains are disjoint from the WM ATTEST/FINAL preimages and the
# trie's 0x00-0x03 node prefixes. There is deliberately NO batch_digest: under
# content-addressed roots the (from_root,to_root) pair the device computes locally
# already binds the exact logical batch (see ToDo-encrypted_entries/
# batch_update_security_review.md, D4/F2/F3). Rollback is forward-incrementing
# (to_counter = from_counter + 1), so the counter is the anti-replay epoch (F1).
# ---------------------------------------------------------------------------

# Benchmark toggle. When True, perform_batch ALSO produces the Ed25519 SigCommit
# over the AuthCommit preimage. The symmetric K_head/K_auth MACs are produced
# regardless. Flip for the MAC-only vs MAC+signature benchmark (D1).
WARD_KSIG = False

_TAG_HEAD = b"WARD HEAD v1"
_TAG_COMMIT = b"WARD COMMIT v1"
_TAG_REVERT = b"WARD REVERT v1"

# Canonical 32-byte stand-in for the empty tree in MAC preimages: empty = H(0x03)
# (ward-design.md §2.2). The proof/root machine uses `root is None` for empty; the
# transition MACs need a fixed-width value, so None maps to this sentinel here.
EMPTY_ROOT_HASH = sha256d(b"\x03")


def _root_or_empty(root) -> bytes:
    """Map a possibly-None root to its 32-byte MAC-preimage form."""
    return EMPTY_ROOT_HASH if root is None else root


async def _derive_ward_key(leaf: bytes) -> bytes:
    """SLIP21(seed, [b"ward", leaf]).key() -- the shared m/"ward" key family
    (K_head/K_auth/K_sig). Seed-scoped; the wallet binding is ward_id inside each
    preimage. Mirrors `_derive_k_index`/`_derive_k_data`."""
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"ward", leaf])
    return node.key()


def head_mac(k_head: bytes, ward_id: bytes, counter: int, root) -> bytes:
    """head_mac = MAC(K_head, TAG_HEAD || ward_id || counter(4B BE) || root). An
    integrity token for the head tuple, NOT a freshness token (freshness is the WM
    nonce challenge) -- always verify it bound to the counter, never by root alone."""
    return _compute_mac(
        k_head, _TAG_HEAD, ward_id, counter.to_bytes(4, "big"), _root_or_empty(root)
    )


def _transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
) -> bytes:
    return (
        tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + _root_or_empty(from_root)
        + to_counter.to_bytes(4, "big")
        + _root_or_empty(to_root)
    )


def auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
) -> bytes:
    """AuthCommit MAC over the forward transition (no batch_digest, D4)."""
    return _compute_mac(
        k_auth,
        _transition_preimage(
            _TAG_COMMIT, ward_id, from_counter, from_root, to_counter, to_root
        ),
    )


def auth_revert(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
) -> bytes:
    """AuthRevert MAC over a one-step rollback. to_counter = from_counter + 1
    (forward-increment, F1); to_root is the restored predecessor root."""
    return _compute_mac(
        k_auth,
        _transition_preimage(
            _TAG_REVERT, ward_id, from_counter, from_root, to_counter, to_root
        ),
    )


def verify_auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
    mac: bytes,
) -> bool:
    """Constant-time-ish equality check of an AuthCommit MAC (another-Trezor verify
    and replay-before-delete)."""
    from trezor import utils

    expected = auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root
    )
    return utils.consteq(expected, mac)


def verify_auth_revert(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
    mac: bytes,
) -> bool:
    """Equality check of an AuthRevert MAC (finalize + another-Trezor verify)."""
    from trezor import utils

    expected = auth_revert(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root
    )
    return utils.consteq(expected, mac)


def verify_chain_step(k_auth, ward_id, running_counter, running_root, link):
    """One step of the another-Trezor AuthCommit-chain verify (Phase 4a). `link` is
    `(from_counter, from_root, to_counter, to_root, auth_commit)` (roots in 32-byte
    MAC-preimage form, EMPTY_ROOT_HASH for empty). Enforces contiguity against the
    running head, a +1 counter step, and that the transition is Trezor-authorized
    (`verify_auth_commit`). Returns the advanced `(to_counter, to_root)`, or raises
    ValueError. Pure + O(1) — the device holds only the running head, never a trie."""
    from_counter, from_root, to_counter, to_root, auth_commit_mac = (
        link[0],
        link[1],
        link[2],
        link[3],
        link[4],
    )
    if from_counter != running_counter:
        raise ValueError("chain: non-contiguous counter")
    if _root_or_empty(from_root) != _root_or_empty(running_root):
        raise ValueError("chain: non-contiguous root")
    if to_counter != running_counter + 1:
        raise ValueError("chain: counter must increment by exactly one")
    if not verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, auth_commit_mac
    ):
        raise ValueError("chain: AuthCommit invalid (unauthorized transition)")
    return to_counter, to_root


def sig_commit(k_sig_secret: bytes, preimage: bytes) -> bytes:
    """Ed25519 signature over the AuthCommit preimage (config-gated benchmark path,
    WARD_KSIG). Fixed preimage only -- never a generic sign-arbitrary-bytes API."""
    from trezor.crypto.curve import ed25519

    return ed25519.sign(k_sig_secret, preimage)


def k_sig_pubkey(k_sig_secret: bytes) -> bytes:
    from trezor.crypto.curve import ed25519

    return ed25519.publickey(k_sig_secret)


# ---------------------------------------------------------------------------
# Root/MAC + pending-queue helpers (formerly apps.ward.__init__).
# ---------------------------------------------------------------------------


def compute_root(
    entry_key_: bytes,
    old_leaf,
    new_leaf,
    proof: list[bytes],
    stored_root: bytes | None,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> bytes | None:
    """Verify the old-state proof against stored_root and return the candidate new
    root (None if the tree becomes/stays empty). `old_leaf`/`new_leaf` are
    (nonce, tag, ct) tuples or None (INSERT/DELETE)."""
    return compute_new_root(
        entry_key_,
        old_leaf,
        new_leaf,
        proof,
        stored_root,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
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
    app_id: bytes = b"",
    key_type: bytes = b"",
    device_id: int = 0,
) -> None:
    """Store an approved edit intent as PENDING under pending_id (pull model)."""
    import storage.ward_store as ward_store

    ward_store.queue_put(
        wallet_id,
        pending_id,
        counter,
        address,
        old_value,
        new_value,
        app_id,
        key_type,
        device_id,
    )


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


async def discard(
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
                "discard: dropped %d candidate(s) for wallet_id=%s",
                dropped,
                wallet_id,
            )
        return None, wallet_id

    rec = ward_store.queue_get(wallet_id, pending_id)
    if rec is None:
        return None, wallet_id
    _counter, _state, address, _ov, _nv, _root, _mac, _app_id, _kt, _did = rec
    ward_store.queue_drop(wallet_id, pending_id)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "discard: dropped pending_id=%d for wallet_id=%s",
            pending_id,
            wallet_id,
        )

    return address, wallet_id


async def lookup_label(
    app_id,
    address: bytes,
    nonce: bytes,
    tag: bytes,
    ct: bytes,
    proof: list[bytes],
    key_type: str = _ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes | None:
    """On-device membership label lookup: authenticate the leaf blob (nonce, tag,
    ct) at entry_key against the active wallet's stored root and, if it verifies,
    decrypt and return the value; else None (or empty tree). The proof is verified
    over entry_key = HMAC(K_index, app_id||0x00||key_type||0x00||device_id||address).
    """
    import storage.ward_head as ward_head

    wallet_id = await _get_wallet_id()
    present, stored_root = ward_head.root_get(wallet_id)
    if not present or stored_root is None:
        return None
    k_index = await _derive_k_index()
    ek = entry_key(k_index, app_id, address, key_type, device_id)
    if not verify_proof(ek, nonce, tag, ct, proof, stored_root):
        return None
    k_data = await _derive_k_data(key_type)
    _c, _id, value = decrypt_leaf(k_data, ek, key_type, nonce, tag, ct)
    return value


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


def _acl_allows(app_id, capability: str) -> bool:
    """WARD-service access-control seam for writes.

    The write path is governed here, inside the trust anchor -- not by the Core
    gateway's read/lookup capability allowlist. The application names the target
    domain (app_id) and this decides whether that write is permitted. MVP: a
    permissive stub (the user is the on-device authorizer via _confirm_update, and
    the round is structurally bound to entry_key so a write can never reach another
    domain's leaf). Real per-app rules land here later."""
    return True


async def _confirm_update(app_id, address: bytes, new_value: bytes) -> None:
    """Trusted on-device confirmation of a WARD edit intent. Shows the target
    domain (app_id) so the user approves "change the <domain> entry for X". Raises
    ActionCancelled if the user rejects; returns normally on approval."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    if len(new_value) == 0:
        title = "Delete WARD entry"
    else:
        title = "Queue WARD entry"

    # PropertyType is a 3-tuple (name, value, is_data); is_data=True renders the
    # value as monospace data. The domain is shown first: it is the on-device
    # authorization that binds this write to entry_key(app_id, address).
    props = [("Domain", _display_bytes(app_id), False), ("Key", _display_bytes(address), True)]
    if len(new_value) != 0:
        props.append(("New value", _display_bytes(new_value), True))

    await confirm_properties(
        "ward_update",
        title,
        props,
        hold=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def queue(
    app_id,
    address: bytes,
    new_value: bytes,
    key_type: str = _ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> tuple[int, bytes]:
    """Queue an edit INTENT (pull model) for the domain named by app_id. Checks the
    write against the WARD-service ACL, shows the queued change (with its domain) on
    a trusted screen and, ONLY on user approval, allocates a pending_id and stores
    the intent PENDING together with app_id, key_type and device_id -- binding the
    whole round to entry_key(app_id, key_type, device_id, address). Under the strict
    counter model the candidate counter is NOT
    derived here: queueing captures user intent only. counter_T is first derived
    inside the WM-synchronized commit flow (WARDPerformUpdate), against the attested
    round state. No proof is taken and the root is NOT computed here either. Returns
    (pending_id, wallet_id). Raises ActionCancelled if the user rejects, DataError
    on invariant violation or when the ACL denies the write.
    """
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if not _acl_allows(app_id, "update"):
        raise DataError("app not authorized for WARD update")
    app_id_b = app_id.encode() if isinstance(app_id, str) else (app_id or b"")

    wallet_id = await _get_wallet_id()

    # Multi-slot queue: several intents may be in flight per wallet, bounded by the
    # storage cap. Committing stays serialized by counter (see finalize).
    if ward_store.queue_count(wallet_id) >= ward_store.MAX_PENDING:
        raise DataError("pending queue is full for this wallet")

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "queue: confirm intent wallet_id=%s address=%s new_value_len=%d",
            wallet_id,
            address,
            len(new_value),
        )

    # Trusted confirmation gates the intent (WP-F5). Raises on user rejection.
    await _confirm_update(app_id_b, address, new_value)

    pending_id = ward_store.queue_alloc_id()
    # counter_T left unset (0) at queue time; derived at WARDPerformUpdate. key_type is
    # framed as bytes; device_id scopes to a per-device slot (§5.1).
    ward_store.queue_put(
        wallet_id,
        pending_id,
        0,
        address,
        b"",
        new_value,
        app_id_b,
        key_type.encode(),
        device_id,
    )

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "queue: queued intent wallet_id=%s pending_id=%d",
            wallet_id,
            pending_id,
        )

    return pending_id, wallet_id


async def lookup(
    app_id,
    address: bytes,
    nonce: bytes | None,
    tag: bytes | None,
    ct: bytes | None,
    proof: list[bytes],
    key_type: str = _ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Verify a membership / non-membership proof against the device's
    authenticated root. Returns (valid, counter, membership, wallet_id, ward_id).

    The target path is formed on-device: entry_key = HMAC(K_index,
    app_id||0x00||key_type||0x00||device_id||address). Membership carries the leaf
    blob (nonce, tag, ct); a non-membership witness is two hashes only
    (witness_entry_key, witness_commit), used opaquely.
    """
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    membership_query = witness_entry_key is None and ct is not None

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()
    present, stored_root = ward_head.root_get(wallet_id)
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

    k_index = await _derive_k_index()
    ek = entry_key(k_index, app_id, address, key_type, device_id)
    if not membership_query:
        if witness_commit is None:
            raise DataError("witness_commit required for non-membership proof")
        valid = verify_nonmembership(
            ek, witness_entry_key, witness_commit, proof, stored_root
        )
        membership = False
    else:
        valid = verify_proof(ek, nonce, tag, ct, proof, stored_root)
        membership = True

    if __debug__:
        from trezor import log

        # Explicit outcome so a proof FAILURE is visible in the log rather than silently
        # collapsing to "unknown" upstream. A membership proof that does not verify is
        # the case that previously produced no message at all.
        log.debug(
            __name__,
            "lookup: query=%s valid=%s (%s proof %s)",
            "membership" if membership_query else "non-membership",
            valid,
            "membership" if membership else "non-membership",
            "OK" if valid else "FAILED verification",
        )

    return valid, ward_store.get_counter(wallet_id), membership, wallet_id, ward_id


async def intent(pending_id: int | None) -> tuple[int, bytes]:
    """Resolve pending_id to (resolved_pending_id, entry_key) for the active wallet.
    The Core gateway calls this to build the WARDProofRequest carrying the opaque
    entry_key (computed on-device from the queued intent's app_id/address) before
    pulling the proof for WARDPerformUpdate. The host serves the proof purely by
    entry_key and never learns the identifier or domain. The pending record's
    key_type/device_id scope the derived entry_key (empty key_type => "address")."""
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)
    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, address, _ov, _nv, _root, _mac, app_id, kt, device_id = rec
    key_type = kt.decode() if kt else _ENTRY_TYPE_ADDRESS

    k_index = await _derive_k_index()
    ek = entry_key(k_index, app_id, address, key_type, device_id)

    if __debug__:
        from trezor import log

        log.debug(__name__, "intent: wallet_id=%s pending_id=%d", wallet_id, pid)

    return pid, ek


async def perform(
    pending_id: int | None,
    ack_nonce: bytes | None,
    ack_tag: bytes | None,
    ack_ct: bytes | None,
    proof: list[bytes],
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple:
    """Authorize a queued intent using a proof the device PULLED on demand.

    The pulled ack is the authoritative current state: (nonce, tag, ct) for a
    membership leaf (UPDATE/DELETE), witness_* for non-membership (INSERT), or empty
    for an empty tree (INIT). The device derives counter_T = current authenticated
    counter + 1, encrypts the queued new_value into a fresh leaf blob (the device is
    the encryptor, §4), computes (root_T, mac_T), persists counter_T, and marks the
    intent COMMITTED. Since the host cannot compute the encrypted leaf itself, the
    new blob (entry_key, entry_type, nonce, tag, ct) is returned so the host can
    store it (ct empty => DELETE). Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id, entry_key, entry_type, nonce, tag, ct).

    key_type/device_id are read from the pending record (framed at queue time), so the
    candidate lands on the scoped entry_key the user approved (empty key_type =>
    "address"). entry_type in the returned blob echoes the resolved key_type.
    """
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)

    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, address, _old_value, new_value, _root, _mac, app_id, kt, device_id = (
        rec
    )
    key_type = kt.decode() if kt else _ENTRY_TYPE_ADDRESS
    k_index = await _derive_k_index()
    # Bind the candidate to its domain/scope: entry_key = HMAC(K_index, scope||id),
    # so this write can only ever produce a leaf under the scope the user approved.
    ek = entry_key(k_index, app_id, address, key_type, device_id)

    # Strict model: derive the candidate counter now, from the device's floor.
    counter_t = ward_store.get_counter(wallet_id) + 1

    present, stored_root = ward_head.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT (see gaps.md #1): empty tree only when the floor is 0.
        if ward_store.get_counter(wallet_id) == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    # membership ack (UPDATE/DELETE) carries the old leaf blob; witness => INSERT.
    old_leaf = None
    if ack_ct is not None and witness_entry_key is None:
        old_leaf = (ack_nonce, ack_tag, ack_ct)

    # The device encrypts the queued new_value into a fresh leaf (empty => DELETE).
    deleting = len(new_value) == 0
    if deleting:
        new_leaf = None
        out_nonce, out_tag, out_ct = b"", b"", b""
    else:
        k_data = await _derive_k_data(key_type)
        out_nonce, out_tag, out_ct = encrypt_leaf(
            k_data, ek, key_type, counter_t, address, new_value
        )
        new_leaf = (out_nonce, out_tag, out_ct)

    try:
        root_t = compute_new_root(
            ek,
            old_leaf,
            new_leaf,
            proof,
            stored_root,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
        )
    except ValueError as e:
        raise DataError(str(e))

    if root_t is not None:
        mac_key = await _derive_mac_key(b"root_mac")
        mac_t = _compute_mac(mac_key, wallet_id, counter_t.to_bytes(4, "big"), root_t)
    else:
        mac_t = None

    ward_store.queue_set_computed(wallet_id, pid, counter_t, root_t, mac_t)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "perform: candidate wallet_id=%s pending_id=%d counter_T=%d root_T=%s",
            wallet_id,
            pid,
            counter_t,
            "EMPTY" if root_t is None else "set",
        )

    ward_id = await _get_ward_id()
    return (
        counter_t,
        root_t,
        mac_t,
        wallet_id,
        ward_id,
        ek,
        key_type,
        out_nonce,
        out_tag,
        out_ct,
    )


async def finalize(
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
    counter, state, _address, _old_value, _new_value, root, mac, _app_id, _kt, _did = rec

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
            "finalize: verify pending_id=%d wallet_id=%s counter_msg=%d mac_present=%s",
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
    import storage.ward_head as ward_head

    ward_head.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter)
    ward_store.queue_drop(wallet_id, pid)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "finalize: installed wallet_id=%s counter=%d root=%s",
            wallet_id,
            counter,
            "EMPTY" if root is None else "set",
        )

    return counter, root, wallet_id, mac


async def perform_batch(pending_ids: list, acks: list) -> tuple:
    """Authorize a BATCH of queued intents as ONE root transition (batch-update).

    `pending_ids` is the ordered set of queued candidates committed together; `acks`
    is the matching list of pulled pre-state acks (one per pending_id), each a 6-tuple
    `(nonce, tag, ct, proof, witness_entry_key, witness_commit)` with the same meaning
    as single-leaf `perform`: membership `(nonce,tag,ct)` for UPDATE/DELETE, `witness_*`
    for INSERT, empty for INIT. The Core gateway pulls these (one WARDProofRequest per
    entry_key) before calling.

    The device computes `to_root` over ALL leaves against the current head, stamps
    every leaf `C_leaf = to_counter = floor + 1` (the whole batch is ONE transition),
    encrypts each new leaf (random nonce, §4.5), enforces per-leaf `C_new > C_old`
    (§4.5/F12), and authenticates the transition with `head_mac` + `AuthCommit`
    (+ `SigCommit` when WARD_KSIG). It stores a single committed batch envelope and
    returns `(to_counter, from_root, to_root, mac_t, head_mac, auth_commit, sig,
    ward_id, leaves)` (from_root in its 32-byte MAC-preimage form,
    EMPTY_ROOT_HASH if empty; to_root is None if the tree becomes empty) where
    `leaves` is a list of `(entry_key, entry_type, nonce, tag, ct)` for the host to
    store (ct empty => DELETE)."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if not pending_ids or len(pending_ids) != len(acks):
        raise DataError("empty or mismatched batch")

    wallet_id = await _get_wallet_id()
    from_counter = ward_store.get_counter(wallet_id)
    to_counter = from_counter + 1  # whole batch = one transition (uniform +1)

    present, stored_root = ward_head.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT: empty tree only when the floor is 0 (mirrors `perform`).
        if from_counter == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    k_index = await _derive_k_index()

    ops = []  # (entry_key, old_leaf, new_leaf, proof, witness_ek, witness_commit)
    leaves = []  # (entry_key, entry_type, nonce, tag, ct) to return to the host
    for i in range(len(pending_ids)):
        pid = pending_ids[i]
        ack = acks[i]
        ack_nonce, ack_tag, ack_ct, proof, w_ek, w_commit = (
            ack[0],
            ack[1],
            ack[2],
            ack[3],
            ack[4],
            ack[5],
        )

        rec = ward_store.queue_get(wallet_id, pid)
        if rec is None:
            raise DataError("no queued intent to perform in batch")
        _c, _s, address, _ov, new_value, _r, _m, app_id, kt, device_id = rec
        key_type = kt.decode() if kt else _ENTRY_TYPE_ADDRESS
        ek = entry_key(k_index, app_id, address, key_type, device_id)

        # membership ack (UPDATE/DELETE) carries the old blob; witness => INSERT.
        old_leaf = None
        if ack_ct is not None and w_ek is None:
            old_leaf = (ack_nonce, ack_tag, ack_ct)
            # Leaf-splicing / counter-monotonicity (§4.5, F12): decrypt the current
            # leaf and require the new stamp to strictly exceed the old one. With the
            # whole batch at to_counter, this holds iff the old leaf predates the head.
            k_data_old = await _derive_k_data(key_type)
            c_old, _id_old, _v_old = decrypt_leaf(
                k_data_old, ek, key_type, ack_nonce, ack_tag, ack_ct
            )
            if to_counter <= c_old:
                raise DataError("C_new is not ahead of C_old (stale leaf)")

        # Encrypt the new leaf (empty new_value => DELETE).
        if len(new_value) == 0:
            new_leaf = None
            out_nonce, out_tag, out_ct = b"", b"", b""
        else:
            k_data = await _derive_k_data(key_type)
            out_nonce, out_tag, out_ct = encrypt_leaf(
                k_data, ek, key_type, to_counter, address, new_value
            )
            new_leaf = (out_nonce, out_tag, out_ct)

        ops.append((ek, old_leaf, new_leaf, proof, w_ek, w_commit))
        leaves.append((ek, key_type, out_nonce, out_tag, out_ct))

    # Fold all leaves into one successor root (order-independent, no sort; rejects a
    # duplicate entry_key within the batch). Each proof is against the running root.
    try:
        to_root = compute_batch_root(stored_root, ops)
    except ValueError as e:
        raise DataError(str(e))

    # Root MAC the WM co-signs at finalize (None root => empty tree => all-zero MAC).
    if to_root is not None:
        mac_key = await _derive_mac_key(b"root_mac")
        mac_t = _compute_mac(mac_key, wallet_id, to_counter.to_bytes(4, "big"), to_root)
    else:
        mac_t = None

    # Transition authentication. Roots are folded to their 32-byte MAC-preimage form
    # (EMPTY_ROOT_HASH for empty) and stored in that form, so a verifying device reads
    # exactly what was MAC'd.
    ward_id = await _get_ward_id()
    from_root_b = _root_or_empty(stored_root)
    to_root_b = _root_or_empty(to_root)
    k_head = await _derive_ward_key(b"K_head")
    k_auth = await _derive_ward_key(b"K_auth")
    head_mac_v = head_mac(k_head, ward_id, to_counter, to_root)
    auth_commit_v = auth_commit(
        k_auth, ward_id, from_counter, from_root_b, to_counter, to_root_b
    )
    sig = b""
    if WARD_KSIG:
        k_sig = await _derive_ward_key(b"K_sig")
        preimage = _transition_preimage(
            _TAG_COMMIT, ward_id, from_counter, from_root_b, to_counter, to_root_b
        )
        sig = sig_commit(k_sig, preimage)

    ward_store.batch_put(
        wallet_id,
        from_counter,
        to_counter,
        from_root_b,
        to_root_b,
        mac_t if mac_t is not None else _ZERO_MAC,
        head_mac_v,
        auth_commit_v,
        sig,
        pending_ids,
    )

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "perform_batch: wallet_id=%s n=%d from=%d to=%d to_root=%s ksig=%s",
            wallet_id,
            len(pending_ids),
            from_counter,
            to_counter,
            "EMPTY" if to_root is None else "set",
            "yes" if WARD_KSIG else "no",
        )

    return (
        to_counter,
        from_root_b,
        to_root,
        mac_t,
        head_mac_v,
        auth_commit_v,
        sig,
        ward_id,
        leaves,
    )


async def finalize_batch(
    counter_msg: int,
    mac_msg: bytes | None,
    wm_signature: bytes,
) -> tuple:
    """Install a committed BATCH after the WM co-signs its head, then drop the whole
    pending set. The single counter-advancing step for a batch (uniform +1).

    Replay-before-delete / consistency (§4, F7): the WM must co-sign EXACTLY the
    device's committed candidate `(to_counter, mac_t)`, and the stored `AuthCommit`
    (binding `from`→`to`) is re-verified, before anything is installed or dropped. If
    either fails, the queue is left intact. Returns `(to_counter, root, ward_id,
    root_mac)` with `root`/`root_mac` None for an emptied tree."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    env = ward_store.batch_get(wallet_id)
    if env is None:
        raise DataError("no committed batch to finalize")
    if env["kind"] != ward_store.BATCH_COMMIT:
        raise DataError("in-flight transition is a rollback; use WARDConfirmRevertByWM")

    to_counter = env["to_counter"]
    to_root_b = env["to_root"]
    mac = env["mac"]
    msg_mac = mac_msg if mac_msg is not None else _ZERO_MAC

    if counter_msg != to_counter or msg_mac != mac:
        raise DataError("confirmation does not match the committed batch")

    ward_id = await _get_ward_id()
    if not verify_ward_final(ward_id, to_counter, mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    # Re-verify the transition authorization (F7: AuthCommit binds from->to).
    k_auth = await _derive_ward_key(b"K_auth")
    if not verify_auth_commit(
        k_auth,
        ward_id,
        env["from_counter"],
        env["from_root"],
        to_counter,
        to_root_b,
        env["auth_commit"],
    ):
        raise DataError("batch AuthCommit verification failed")

    # Anti-rollback: the finalized counter must exceed the durable local floor.
    if to_counter <= ward_store.get_counter(wallet_id):
        raise DataError("counter_T is not ahead of counter_loc")

    # Map the empty-tree sentinel back to None for installation.
    root_install = None if to_root_b == EMPTY_ROOT_HASH else to_root_b
    ward_head.root_set(wallet_id, root_install)
    ward_store.commit_counter(wallet_id, to_counter)
    for pid in env["pending_ids"]:
        ward_store.queue_drop(wallet_id, pid)
    ward_store.batch_clear(wallet_id)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "finalize_batch: installed wallet_id=%s counter=%d n=%d root=%s",
            wallet_id,
            to_counter,
            len(env["pending_ids"]),
            "EMPTY" if root_install is None else "set",
        )

    root_mac = None if mac == _ZERO_MAC else mac
    return to_counter, root_install, ward_id, root_mac


async def perform_revert(
    stuck_counter: int,
    stuck_root: bytes,
    prev_root: bytes,
    forward_auth_commit: bytes,
) -> tuple:
    """Prepare a constrained one-step rollback (ward-design.md §8.2, batch-update).

    The host presents the **forward `AuthCommit` that created the current stuck head**
    (`stuck_counter`, `stuck_root`) together with the predecessor `prev_root` it
    encodes. Because `K_auth` is seed-shared, this device verifies that MAC to learn,
    cryptographically, that `prev_root` was the immediate predecessor of `stuck_root`
    (F6 — the predecessor is proven by the device family's own signature, NOT by the
    WM). The demotion is **forward-incrementing** (`to_counter = stuck_counter + 1`,
    head → `prev_root`), so the counter stays strictly monotone and a stale
    authorization can never replay after the rollback (F1). All roots are 32-byte
    MAC-preimage form (EMPTY_ROOT_HASH for empty).

    Stores a BATCH_REVERT envelope and returns `(to_counter, from_root, to_root,
    mac_t, head_mac, auth_revert, sig, ward_id)`."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if stuck_counter < 1:
        raise DataError("cannot roll back the genesis head")

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()

    # The stuck head MUST be exactly the current authenticated head — bind the COUNTER,
    # not just the root (roots are content-addressed and repeat; §2.4/§8.2 point 2).
    cur_counter = ward_store.get_counter(wallet_id)
    _present, cur_root = ward_head.root_get(wallet_id)
    if stuck_counter != cur_counter or _root_or_empty(cur_root) != stuck_root:
        raise DataError("stuck head does not match the current authenticated head")

    # Verify the forward AuthCommit (stuck_counter-1, prev_root) -> (stuck_counter,
    # stuck_root). Its validity proves prev_root is the immediate predecessor and
    # fixes the demotion target — it is not a host-named free-form root (§8.2 point 3).
    k_auth = await _derive_ward_key(b"K_auth")
    if not verify_auth_commit(
        k_auth,
        ward_id,
        stuck_counter - 1,
        prev_root,
        stuck_counter,
        stuck_root,
        forward_auth_commit,
    ):
        raise DataError("forward AuthCommit invalid; cannot prove the predecessor")

    to_counter = stuck_counter + 1  # forward-increment (F1), even though root goes back
    to_root = None if prev_root == EMPTY_ROOT_HASH else prev_root

    if to_root is not None:
        mac_key = await _derive_mac_key(b"root_mac")
        mac_t = _compute_mac(mac_key, wallet_id, to_counter.to_bytes(4, "big"), to_root)
    else:
        mac_t = None

    auth_revert_v = auth_revert(k_auth, ward_id, stuck_counter, stuck_root, to_counter, prev_root)
    k_head = await _derive_ward_key(b"K_head")
    head_mac_v = head_mac(k_head, ward_id, to_counter, to_root)
    sig = b""
    if WARD_KSIG:
        k_sig = await _derive_ward_key(b"K_sig")
        sig = sig_commit(
            k_sig,
            _transition_preimage(
                _TAG_REVERT, ward_id, stuck_counter, stuck_root, to_counter, prev_root
            ),
        )

    ward_store.batch_put(
        wallet_id,
        stuck_counter,
        to_counter,
        stuck_root,
        prev_root,
        mac_t if mac_t is not None else _ZERO_MAC,
        head_mac_v,
        auth_revert_v,
        sig,
        [],
        ward_store.BATCH_REVERT,
    )

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "perform_revert: wallet_id=%s stuck=%d -> to=%d (root back to %s)",
            wallet_id,
            stuck_counter,
            to_counter,
            "EMPTY" if to_root is None else "prev",
        )

    return (
        to_counter,
        stuck_root,
        to_root,
        mac_t,
        head_mac_v,
        auth_revert_v,
        sig,
        ward_id,
    )


async def finalize_revert(
    counter_msg: int,
    mac_msg: bytes | None,
    wm_signature: bytes,
) -> tuple:
    """Install a one-step rollback after the WM co-signs the demoted head. Mirrors
    `finalize_batch` but verifies the stored **AuthRevert** and requires a
    BATCH_REVERT envelope. Forward-incrementing, so the anti-rollback counter guard
    still holds. Returns `(to_counter, root, ward_id, root_mac)`."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    env = ward_store.batch_get(wallet_id)
    if env is None:
        raise DataError("no committed rollback to finalize")
    if env["kind"] != ward_store.BATCH_REVERT:
        raise DataError("in-flight transition is a commit; use WARDConfirmBatchByWM")

    to_counter = env["to_counter"]
    to_root_b = env["to_root"]
    mac = env["mac"]
    msg_mac = mac_msg if mac_msg is not None else _ZERO_MAC

    if counter_msg != to_counter or msg_mac != mac:
        raise DataError("confirmation does not match the committed rollback")

    ward_id = await _get_ward_id()
    if not verify_ward_final(ward_id, to_counter, mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    k_auth = await _derive_ward_key(b"K_auth")
    if not verify_auth_revert(
        k_auth,
        ward_id,
        env["from_counter"],
        env["from_root"],
        to_counter,
        to_root_b,
        env["auth_commit"],
    ):
        raise DataError("rollback AuthRevert verification failed")

    if to_counter <= ward_store.get_counter(wallet_id):
        raise DataError("counter_T is not ahead of counter_loc")

    root_install = None if to_root_b == EMPTY_ROOT_HASH else to_root_b
    ward_head.root_set(wallet_id, root_install)
    ward_store.commit_counter(wallet_id, to_counter)
    ward_store.batch_clear(wallet_id)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "finalize_revert: installed wallet_id=%s counter=%d root=%s",
            wallet_id,
            to_counter,
            "EMPTY" if root_install is None else "prev",
        )

    root_mac = None if mac == _ZERO_MAC else mac
    return to_counter, root_install, ward_id, root_mac


async def sync() -> tuple[bytes, int, bytes, bytes]:
    """Begin a sync round: mint a fresh per-round nonce (anti-replay) and store it.
    Also derives and returns the WM-facing ward_id so the host can address the WM
    for this round without inventing it. Returns (nonce, version, wallet_id,
    ward_id)."""
    import storage.ward_head as ward_head
    from trezor.crypto import random

    wallet_id = await _get_wallet_id()
    ward_id = await _get_ward_id()
    nonce = random.bytes(ward_head.NONCE_LENGTH)
    ward_head.sync_begin(wallet_id, nonce)

    if __debug__:
        from trezor import log

        log.debug(__name__, "sync: minted nonce for wallet_id=%s", wallet_id)

    return nonce, _WARD_VERSION, wallet_id, ward_id


async def ingest(
    counter: int, mac_msg: bytes | None, wm_signature: bytes
) -> tuple[int, bytes]:
    """Verify + record the WM freshness attestation for the open sync round.
    Returns (counter, wallet_id)."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    import storage.ward_head as ward_head
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    ctx = ward_head.sync_get(wallet_id)
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

    ward_head.sync_set_attested(wallet_id, counter, mac_msg)

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "ingest: accepted counter=%d for wallet_id=%s",
            counter,
            wallet_id,
        )

    return counter, wallet_id


async def reconcile(
    root: bytes | None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """Adopt the host-supplied root after binding it to the attested mac_ext,
    install (root, counter_ext), advance the ceiling, and clear the round.
    Adopt-only (pending edits go through the write path). Returns
    (counter, new_root, wallet_id, root_mac)."""
    import storage.ward_store as ward_store
    import storage.ward_head as ward_head
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()

    ctx = ward_head.sync_get(wallet_id)
    if ctx is None or ctx[1] != ward_head.SYNC_ATTESTED:
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

    ward_head.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter_ext)
    ward_head.sync_clear()

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "reconcile: adopted counter=%d root=%s wallet_id=%s",
            counter_ext,
            "EMPTY" if root is None else "set",
            wallet_id,
        )

    return counter_ext, root, wallet_id, mac_ext


async def verify_chain(links: list) -> tuple:
    """Another-Trezor CHAIN verification + adopt (Phase 4a, read-only). Instead of
    trusting a single host-supplied root (reconcile), prove the WM-attested head sits
    on a fully Trezor-authorized canonical path: fold the ordered `links` from the
    device's trusted baseline (its current head; genesis `(0, empty)` for a fresh
    device) to the head, verifying per link contiguity + a +1 counter step +
    `AuthCommit` (+ Ed25519 `SigCommit` when WARD_KSIG). O(1) RAM — only the running
    head is kept; roots are NOT reconstructed (each link's AuthCommit means a Trezor
    validated that step's content at write time). The chain must terminate EXACTLY at
    the attested counter from the open sync round, and its terminal root must match the
    attested `mac_ext` (ties the authorized chain to WM freshness + defeats
    root-resurrection). Only then install `root_head`. Each link is
    `(from_counter, from_root, to_counter, to_root, auth_commit, sig_commit|None)`.
    Returns `(counter, new_root, ward_id, root_mac)`."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await _get_wallet_id()
    ctx = ward_head.sync_get(wallet_id)
    if ctx is None or ctx[1] != ward_head.SYNC_ATTESTED:
        raise DataError("no attested sync round to verify against")
    _nonce, _state, counter_ext, mac_ext = ctx

    ward_id = await _get_ward_id()
    k_auth = await _derive_ward_key(b"K_auth")
    k_sig_pub = k_sig_pubkey(await _derive_ward_key(b"K_sig")) if WARD_KSIG else None

    # Trusted baseline = the device's current installed head (fresh device: genesis).
    present, base_root = ward_head.root_get(wallet_id)
    running_counter = ward_store.get_counter(wallet_id)
    running_root = _root_or_empty(base_root if present else None)

    for link in links:
        try:
            running_counter, running_root = verify_chain_step(
                k_auth, ward_id, running_counter, running_root, link
            )
        except ValueError as e:
            raise DataError(str(e))
        if WARD_KSIG:
            from trezor.crypto.curve import ed25519

            sig = link[5] if len(link) > 5 else None
            if sig is None:
                raise DataError("chain: SigCommit required (WARD_KSIG) but missing")
            preimage = _transition_preimage(
                _TAG_COMMIT, ward_id, link[0], link[1], link[2], link[3]
            )
            if not ed25519.verify(k_sig_pub, sig, preimage):
                raise DataError("chain: SigCommit invalid")

    # The authorized chain must land EXACTLY on the WM-attested head.
    if running_counter != counter_ext:
        raise DataError("chain does not terminate at the attested counter")
    root_head = None if running_root == EMPTY_ROOT_HASH else running_root
    if mac_ext is None:
        if root_head is not None:
            raise DataError("attested tree is empty but chain reached a non-empty root")
    else:
        if root_head is None:
            raise DataError("attested tree is non-empty but chain reached the empty tree")
        mac_key = await _derive_mac_key(b"root_mac")
        computed = _compute_mac(
            mac_key, wallet_id, counter_ext.to_bytes(4, "big"), root_head
        )
        if computed != mac_ext:
            raise DataError("chain terminal root does not match the attested mac")

    ward_head.root_set(wallet_id, root_head)
    ward_store.commit_counter(wallet_id, counter_ext)
    ward_head.sync_clear()

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "verify_chain: adopted counter=%d via %d authorized link(s) wallet_id=%s",
            counter_ext,
            len(links),
            wallet_id,
        )

    return counter_ext, root_head, ward_id, mac_ext


async def pending() -> tuple[list[int], list[bytes], bytes, bytes]:
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


async def debug_set_root(
    root: bytes,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    """DEBUG-ONLY unauthenticated root injection (seed a root in one call). Installs
    the root, increments the counter by 1. Rejected on production firmware. Returns
    (counter, new_root, wallet_id, root_mac)."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if not __debug__:
        raise DataError("WARDDebugSetRoot is only accepted in debug builds")

    if len(root) != ward_store.ROOT_LENGTH:
        raise DataError("root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()
    counter = ward_store.bump_counter(wallet_id)
    ward_head.root_set(wallet_id, root)

    mac_key = await _derive_mac_key(b"root_mac")
    new_root = root
    root_mac = (
        _compute_mac(mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )

    return counter, new_root, wallet_id, root_mac
