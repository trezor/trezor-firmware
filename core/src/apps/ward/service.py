"""WARD service — the on-device trust anchor (TW): orchestration and authorisation.

What is left here after the split is everything that needs the DEVICE: storage, the
user, the WM, and the ordering rules between them. The three things that do not are
their own modules, and this one imports them:

    keys    the seed-derived key schedule, and the keyed path an identifier maps to
    leaf    the two-part sealed leaf and its keyless commitment
    trie    proof verification and root derivation -- pure, total, stateless

The split is along what each part needs to be TRUSTED for, not merely along file size.
`trie` takes bytes and returns bytes: it can be checked against published vectors with
no wallet, no storage and no screen in play, which is what makes its soundness
argument reviewable on its own. `leaf` holds the encoding and the AEAD but no key
schedule -- keys arrive as arguments. `keys` holds the schedule and nothing that uses
it. Only this module combines them, and only this module can therefore get the
COMBINATION wrong, which is where the interesting failures live.

What remains here:
  - the WM attestation and the CAS/AuthCommit chain -- who may advance the head
  - the ACL and the trusted screens -- what the user actually approved
  - the queue/perform/finalize state machine, single and batch, and the revert path
  - sync, ingest, reconcile, verify_chain

Layering:
  - persistence  -> storage.ward_store (counter, authenticated root, queue, sync ctx)
  - callers      -> apps.common.ward (Core capability boundary) and the thin
                    host-facing protobuf handlers in apps.ward.*

Production firmware never accepts a host-supplied root.
"""

from micropython import const
from typing import TYPE_CHECKING

from .keys import (
    ENTRY_TYPE_ADDRESS,
    compute_mac,
    derive_k_data,
    derive_k_ident,
    derive_k_path,
    derive_mac_key,
    derive_ward_key,
    entry_key,
    get_wallet_id,
    get_ward_id,
)
from .leaf import (
    EMPTY_PART,
    commit_of,
    decode_content,
    decode_identity,
    encode_content,
    encode_identity,
)
from .trie import (
    TrieWalk,
    compute_batch_root,
    compute_new_root,
    verify_nonmembership,
    verify_proof,
)

if TYPE_CHECKING:
    pass


def sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


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
from apps.ward.wm_config import WM_PUBLIC_KEY as _WM_PUBKEY

_ZERO_PUBKEY = (
    b"\x00" * 32
)  # the "unprovisioned" placeholder value; never verify against it
_ZERO_SIG = (
    b"\x00" * 64
)  # a degenerate signature that must never be accepted (see _verify)

if __debug__:
    # Well-known debug WM public key, accepted only on debug builds. Its 32-byte
    # Ed25519 private seed is the ASCII string b"AUTHDB QM DEBUG KEY SEED v1 ....";
    # tests/tools sign attestations with it.
    _WM_PUBKEY_DEBUG = bytes.fromhex(
        "17b4c21f6b55935405d5a48ee3f2f29f42d78c9a650d8f686a705b21ef62b0b6"
    )

_WARD_ATTEST_DOMAIN = b"WARD ATTEST v2"
_WARD_ATTEST_VERSION = const(2)
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"

# WARD protocol version echoed in the sync round (WARDSyncAck).
_WARD_VERSION = const(2)
# An absent MAC is encoded as all-zero for genesis. Later empty heads carry a MAC.
_ZERO_MAC = b"\x00" * 32


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
    ward_id: bytes,
    nonce: bytes,
    counter: int,
    mac: bytes,
    signature: bytes,
    timestamp: int,
    head_nonce: bytes,
) -> bool:
    """Verify the WM's freshness attestation for a sync round:

        b"WARD ATTEST v1" || version(1B) || nonce || ward_id || counter(4B BE) || mac

    `ward_id` is the SLIP21-derived WM-facing anchor (see `get_ward_id`), NOT the
    20-byte local `wallet_id`; the WM only ever signs over `ward_id`.
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + ward_id
        + counter.to_bytes(4, "big")
        + mac
        + timestamp.to_bytes(8, "big")
        + head_nonce
    )
    return _verify(message, signature)


def verify_ward_final(
    ward_id: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's final attestation over the committed WARD candidate:

        b"WARD FINAL v1" || ward_id || counter(4B BE) || mac

    `ward_id` is the SLIP21-derived WM-facing anchor (see `get_ward_id`).
    """
    message = _WARD_FINAL_DOMAIN + ward_id + counter.to_bytes(4, "big") + mac
    return _verify(message, signature)


async def _confirm_export_keys(key_type: str) -> None:
    """Trusted confirmation before handing WARD keys to the host (PUSH). Exporting
    K_path + K_ident/K_data(key_type) lets the host resolve identifiers to paths and
    read identities and values for this entry type -- a deliberate, user-approved
    downgrade of the "host holds no keys" property. Raises ActionCancelled if the user
    rejects."""
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


async def _confirm_revert(stuck_counter: int) -> None:
    """Trusted confirmation before undoing the most recent WARD change. The device
    cannot name the entries the reverted transition touched -- it holds only roots --
    so the screen identifies the change by its counter. Raises ActionCancelled if the
    user rejects."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "ward_revert",
        "Undo WARD change",
        [
            ("Change", "#" + str(stuck_counter), False),
            ("Warning", "Your entries return to their state before it.", False),
        ],
        hold=True,
        br_code=ButtonRequestType.ProtectCall,
    )


async def export_keys(key_type: str = ENTRY_TYPE_ADDRESS) -> tuple:
    """PUSH key export: after user confirmation, return
    (K_path, K_data(key_type), K_ident(key_type)). K_sig is never exported. The three
    are independent capabilities: K_path resolves identifier -> path, K_ident reads
    identities, K_data reads values -- so an export can grant indexing without
    granting value reads."""
    await _confirm_export_keys(key_type)
    k_path = await derive_k_path()
    k_data = await derive_k_data(key_type)
    k_ident = await derive_k_ident(key_type)
    return k_path, k_data, k_ident


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
# wallet's devices, like K_path/K_ident/K_data); the wallet binding is `ward_id` inside
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
# FIXME(ward, INACTIVE): benchmark toggle, False in every shipped build -- so every
# `if WARD_KSIG` branch below (perform_batch, perform_revert, verify_chain) and
# k_sig_pubkey() are unreachable, and sig_commit is always b"".
WARD_KSIG = True

_TAG_HEAD = b"WARD HEAD v1"
_TAG_COMMIT = b"WARD COMMIT v1"
_TAG_REVERT = b"WARD REVERT v1"

# Canonical 32-byte stand-in for the empty tree in MAC preimages: empty = H(0x02)
# (ward-design.md §2.2). The proof/root machine uses `root is None` for empty; the
# transition MACs need a fixed-width value, so None maps to this sentinel here.
EMPTY_ROOT_HASH = sha256d(b"\x02")


def _root_or_empty(root) -> bytes:
    """Map a possibly-None root to its 32-byte MAC-preimage form."""
    return EMPTY_ROOT_HASH if root is None else root


def head_mac(k_head: bytes, ward_id: bytes, counter: int, root) -> bytes:
    """head_mac = MAC(K_head, TAG_HEAD || ward_id || counter(4B BE) || root). An
    integrity token for the head tuple, NOT a freshness token (freshness is the WM
    nonce challenge) -- always verify it bound to the counter, never by root alone."""
    return compute_mac(
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
    return compute_mac(
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
    return compute_mac(
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


# ACCEPTED (trust model: the WM is trusted for freshness and anti-fork). Every perform
# mints a valid AuthCommit, abandoned candidates included, so a malicious WM can attest an
# abandoned branch that starts at a device's anchor and this chain check will adopt it.
# Closing that would need a WM acceptance signature on every link.
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
    if not (
        verify_auth_commit(
            k_auth,
            ward_id,
            from_counter,
            from_root,
            to_counter,
            to_root,
            auth_commit_mac,
        )
        or verify_auth_revert(
            k_auth,
            ward_id,
            from_counter,
            from_root,
            to_counter,
            to_root,
            auth_commit_mac,
        )
    ):
        raise ValueError("chain: AuthCommit invalid (unauthorized transition)")
    return to_counter, to_root


def sig_commit(k_sig_secret: bytes, preimage: bytes) -> bytes:
    """Ed25519 signature over the AuthCommit preimage (config-gated benchmark path,
    WARD_KSIG). Fixed preimage only -- never a generic sign-arbitrary-bytes API."""
    from trezor.crypto.curve import ed25519

    return ed25519.sign(k_sig_secret, preimage)


def wm_transition_message(
    ward_id,
    from_counter,
    from_root,
    to_counter,
    to_root,
    mac,
    authorization,
    revert=False,
    head_nonce=None,
):
    return (
        b"WARD WM TRANSITION v2"
        + bytes([1 if revert else 0])
        + ward_id
        + from_counter.to_bytes(4, "big")
        + _root_or_empty(from_root)
        + to_counter.to_bytes(4, "big")
        + _root_or_empty(to_root)
        + mac
        + authorization
        + (head_nonce if head_nonce is not None else bytes(32))
    )


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

    wallet_id = await get_wallet_id()

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
    _counter, _state, address, _nv, _root, _mac, _app_id, _kt, _did = rec
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
    caller,
    address: bytes,
    id_part,
    val_part,
    proof: list[bytes],
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes | None:
    """On-device membership label lookup: authenticate the leaf (key_type, id_part,
    val_part) at entry_key against the active wallet's stored root and, if it verifies,
    decrypt and return the value; else None (or empty tree). The proof is verified over
    entry_key = HMAC(K_path, app_id||0x00||key_type||0x00||device_id||address).
    """
    import storage.ward_head as ward_head

    wallet_id = await get_wallet_id()
    present, stored_root = ward_head.root_get(wallet_id)
    if not present or stored_root is None:
        return None
    k_path = await derive_k_path()
    ek = entry_key(
        k_path, caller.app_id, address, key_type, caller.device_slot(device_id)
    )
    if not verify_proof(ek, key_type, id_part, val_part, proof, stored_root):
        return None
    k_data = await derive_k_data(key_type)
    _c, value = decode_content(k_data, ek, key_type, val_part)
    return value


# ---------------------------------------------------------------------------
# Root/MAC + pending-queue helpers (formerly apps.ward.__init__).
# ---------------------------------------------------------------------------


def display_text(value: bytes) -> str | None:
    """`value` as plain text if every byte is printable ASCII and it has no leading or
    trailing space; otherwise None. Plain text is what a trusted screen may show as-is:
    it maps back to exactly one byte string, and no control, zero-width, bidi or
    look-alike character reaches the screen. (The old best-effort rendering decoded any
    UTF-8 and fell back to bare hex, so b"\xff\xfe" and the text "fffe" looked the same
    and a host could make an approval show one key while the device stored another.)"""
    if (
        value
        and all(0x20 <= b <= 0x7E for b in value)
        and value[0] != 0x20
        and value[-1] != 0x20
    ):
        return value.decode()
    return None


def display_property(name: str, value: bytes, is_data: bool = True) -> tuple:
    """A confirm_properties row for `value` that cannot be misread: plain text under
    `name`, anything else as hex under "<name> (hex)", and the empty value under
    "<name> (empty)". The form is named by the LABEL, not marked inside the content, so
    text such as an Ethereum "0x..." address is shown as-is and can never be taken for
    hex."""
    text = display_text(value)
    if text is not None:
        return (name, text, is_data)
    if not value:
        return (name + " (empty)", "-", False)
    return (name + " (hex)", value.hex(), True)


def _acl_allows(caller, capability: str) -> bool:
    """WARD-service access-control seam for writes.

    The write path is governed here, inside the trust anchor -- not by the Core
    gateway's read/lookup capability allowlist. `caller` is the WardCaller the firmware
    established; its domain is the write's target, never a name the app or host gave,
    and this decides whether that write is permitted. MVP: a
    permissive stub (the user is the on-device authorizer via _confirm_update, and
    the round is structurally bound to entry_key so a write can never reach another
    domain's leaf). Real per-app rules land here later."""
    return True


async def _confirm_update(
    app_id, address: bytes, new_value: bytes, delete: bool
) -> None:
    """Trusted on-device confirmation of a WARD edit intent. Shows the target domain
    (app_id) so the user approves "change the <domain> entry for X". Raises
    ActionCancelled if the user rejects; returns normally on approval.

    A DELETE gets its own screen and its own br_name ("ward_delete"): it is a
    destructive, irreversible operation -- the leaf is removed from the trie, not set
    to an empty value -- so it must not be presented as just another edit, and a
    caller/test/input-flow must be able to tell the two button requests apart.

    The screen is chosen by `delete`, the SAME flag that is stored and later decides
    what perform does -- never by the value's length. Keying it on the value let a
    host send delete=True with a non-empty value: the user saw an update, the device
    performed a delete.
    """
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    # PropertyType is a 3-tuple (name, value, is_data); is_data=True renders the
    # value as monospace data. The domain is shown first: it is the on-device
    # authorization that binds this write to entry_key(app_id, address).
    domain = display_property("Domain", app_id, False)
    key = display_property("Key", address)

    if delete:
        await confirm_properties(
            "ward_delete",
            "Delete WARD entry",
            [
                domain,
                key,
                ("Warning", "This entry will be permanently removed.", False),
            ],
            hold=True,
            br_code=ButtonRequestType.ConfirmOutput,
        )
        return

    await confirm_properties(
        "ward_update",
        "Queue WARD entry",
        [domain, key, display_property("New value", new_value)],
        hold=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def queue(
    caller,
    address: bytes,
    new_value: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
    delete: bool = False,
) -> tuple[int, bytes]:
    """Queue an edit INTENT (pull model) in the CALLER's domain (`caller` is an
    apps.ward.caller.WardCaller: the domain comes from its identity, and a device slot
    other than 0x00 is refused unless it is a core app). Checks the
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

    if not _acl_allows(caller, "update"):
        raise DataError("app not authorized for WARD update")
    if delete and len(new_value) != 0:
        raise DataError("a WARD delete carries no new value")
    app_id_b = caller.app_id
    device_id = caller.device_slot(device_id)

    wallet_id = await get_wallet_id()

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
    await _confirm_update(app_id_b, address, new_value, delete)

    pending_id = ward_store.queue_alloc_id()
    # counter_T left unset (0) at queue time; derived at WARDPerformUpdate. key_type is
    # framed as bytes; device_id scopes to a per-device slot (§5.1).
    ward_store.queue_put(
        wallet_id,
        pending_id,
        0,
        address,
        new_value,
        app_id_b,
        key_type.encode(),
        device_id,
        delete,
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
    caller,
    address: bytes,
    id_part,
    val_part,
    proof: list[bytes],
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Verify a membership / non-membership proof against the device's
    authenticated root. Returns (valid, counter, membership, wallet_id, ward_id).

    The target path is formed on-device: entry_key = HMAC(K_path,
    app_id||0x00||key_type||0x00||device_id||address). Membership carries the leaf's
    two parts (id_part, val_part); a non-membership witness is two hashes only
    (witness_entry_key, witness_commit), used opaquely.
    """
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    membership_query = witness_entry_key is None and val_part is not None

    wallet_id = await get_wallet_id()
    ward_id = await get_ward_id()
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

    k_path = await derive_k_path()
    ek = entry_key(
        k_path, caller.app_id, address, key_type, caller.device_slot(device_id)
    )
    if not membership_query:
        if witness_entry_key is None:
            raise DataError("witness_entry_key required for non-membership proof")
        if witness_commit is None:
            raise DataError("witness_commit required for non-membership proof")
        valid = verify_nonmembership(
            ek, witness_entry_key, witness_commit, proof, stored_root
        )
        membership = False
    else:
        try:
            valid = verify_proof(ek, key_type, id_part, val_part, proof, stored_root)
        except ValueError as error:
            raise DataError(str(error))
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

    wallet_id = await get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)
    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, address, _nv, _root, _mac, app_id, kt, device_id = rec
    key_type = kt.decode() if kt else ENTRY_TYPE_ADDRESS

    k_path = await derive_k_path()
    ek = entry_key(k_path, app_id, address, key_type, device_id)

    if __debug__:
        from trezor import log

        log.debug(__name__, "intent: wallet_id=%s pending_id=%d", wallet_id, pid)

    return pid, ek


async def perform(
    pending_id: int | None,
    ack_id_part,
    ack_val_part,
    proof: list[bytes],
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple:
    """Authorize a queued intent using a proof the device PULLED on demand.

    The pulled ack is the authoritative current state: the leaf's two parts
    (ack_id_part, ack_val_part) for a membership leaf (UPDATE/DELETE), witness_* for
    non-membership (INSERT), or empty for an empty tree (INIT). The device derives
    counter_T = current authenticated counter + 1, encodes the queued new_value into a
    fresh leaf -- BOTH parts, so the leaf is self-describing (the device is the
    encryptor, §4) -- computes (root_T, mac_T), persists counter_T, and marks the
    intent COMMITTED. Since the host cannot compute a sealed leaf itself, the new leaf
    (entry_key, key_type, id_part, val_part) is returned so the host can store it. A
    DELETE returns BOTH parts empty: the leaf no longer exists, so the host must
    REMOVE the record at entry_key rather than keep an empty-valued one. Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id, entry_key, key_type, id_part, val_part).

    key_type/device_id are read from the pending record (framed at queue time), so the
    candidate lands on the scoped entry_key the user approved (empty key_type =>
    "address").
    """
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)

    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no queued intent to perform")
    _counter, _state, address, new_value, _root, _mac, app_id, kt, device_id = rec
    key_type = kt.decode() if kt else ENTRY_TYPE_ADDRESS
    k_path = await derive_k_path()
    # Bind the candidate to its domain/scope: entry_key = HMAC(K_path, scope||id),
    # so this write can only ever produce a leaf under the scope the user approved.
    ek = entry_key(k_path, app_id, address, key_type, device_id)

    # Strict model: derive the candidate counter now, from the device's floor.
    counter_t = ward_store.get_counter(wallet_id) + 1

    present, stored_root = ward_head.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT (see gaps.md #1): empty tree only when the floor is 0.
        if ward_store.get_counter(wallet_id) == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    # membership ack (UPDATE/DELETE) carries the old leaf's parts; witness => INSERT.
    old_leaf = None
    if ack_val_part is not None and witness_entry_key is None:
        old_leaf = (key_type, ack_id_part, ack_val_part)

    # The device encodes the queued write into a fresh leaf. A DELETE is a FULL
    # removal: the leaf ceases to exist in the trie (compute_new_root collapses its
    # parent), so there is no leaf left to describe -- BOTH parts are empty and the
    # host must drop the record, not keep an empty-valued one.
    deleting = ward_store.queue_is_delete(wallet_id, pid)
    if deleting:
        new_leaf = None
        out_id_part = EMPTY_PART
        out_val_part = EMPTY_PART
    else:
        k_ident = await derive_k_ident(key_type)
        k_data = await derive_k_data(key_type)
        out_id_part = encode_identity(k_ident, ek, key_type, address, app_id, device_id)
        out_val_part = encode_content(k_data, ek, key_type, counter_t, new_value)
        new_leaf = (key_type, out_id_part, out_val_part)

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

    mac_key = await derive_mac_key(b"root_mac")
    mac_t = compute_mac(
        mac_key, wallet_id, counter_t.to_bytes(4, "big"), _root_or_empty(root_t)
    )

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

    ward_id = await get_ward_id()
    return (
        counter_t,
        root_t,
        mac_t,
        wallet_id,
        ward_id,
        ek,
        key_type,
        out_id_part,
        out_val_part,
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

    wallet_id = await get_wallet_id()
    pid = await _resolve_pending_id(wallet_id, pending_id)

    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        raise DataError("no candidate to finalize")
    counter, state, _address, _new_value, root, mac, _app_id, _kt, _did = rec

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

    ward_id = await get_ward_id()
    if not verify_ward_final(ward_id, counter, candidate_mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    # Anti-rollback: the finalized counter must exceed the durable local floor.
    if counter <= ward_store.get_counter(wallet_id):
        raise DataError("counter_T is not ahead of counter_loc")

    # Install the volatile authenticated root and persist only counter_loc.
    import storage.ward_head as ward_head

    ward_head.root_set(wallet_id, root)
    ward_store.commit_counter(wallet_id, counter)
    await _cache_after_commit(wallet_id, pid, counter)
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
    `leaves` is a list of `(entry_key, key_type, id_part, val_part)` for the host to
    store (ct empty => DELETE)."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if not pending_ids or len(pending_ids) != len(acks):
        raise DataError("empty or mismatched batch")

    wallet_id = await get_wallet_id()
    from_counter = ward_store.get_counter(wallet_id)
    to_counter = from_counter + 1  # whole batch = one transition (uniform +1)

    present, stored_root = ward_head.root_get(wallet_id)
    if not present:
        # Fresh-wallet INIT: empty tree only when the floor is 0 (mirrors `perform`).
        if from_counter == 0:
            stored_root = None
        else:
            raise DataError("no authenticated root in session")

    k_path = await derive_k_path()

    ops = []  # (entry_key, old_leaf, new_leaf, proof, witness_ek, witness_commit)
    leaves = []  # (entry_key, key_type, id_part, val_part) to return to the host
    for i in range(len(pending_ids)):
        pid = pending_ids[i]
        ack = acks[i]
        ack_id_part, ack_val_part, proof, w_ek, w_commit = (
            ack[0],
            ack[1],
            ack[2],
            ack[3],
            ack[4],
        )

        rec = ward_store.queue_get(wallet_id, pid)
        if rec is None:
            raise DataError("no queued intent to perform in batch")
        _c, _s, address, new_value, _r, _m, app_id, kt, device_id = rec
        key_type = kt.decode() if kt else ENTRY_TYPE_ADDRESS
        ek = entry_key(k_path, app_id, address, key_type, device_id)

        # membership ack (UPDATE/DELETE) carries the old leaf's parts; witness => INSERT.
        old_leaf = None
        if ack_val_part is not None and w_ek is None:
            old_leaf = (key_type, ack_id_part, ack_val_part)
            # Leaf-splicing / counter-monotonicity (§4.5, F12): decrypt the current
            # leaf's content part and require the new stamp to strictly exceed the old
            # one. With the whole batch at to_counter, this holds iff the old leaf
            # predates the head.
            k_data_old = await derive_k_data(key_type)
            c_old, _v_old = decode_content(k_data_old, ek, key_type, ack_val_part)
            if to_counter <= c_old:
                raise DataError("C_new is not ahead of C_old (stale leaf)")

        # Encode the new leaf. A DELETE is a FULL removal: the leaf ceases to exist, so
        # both parts are empty and the host drops the record.
        if ward_store.queue_is_delete(wallet_id, pid):
            new_leaf = None
            out_id_part = EMPTY_PART
            out_val_part = EMPTY_PART
        else:
            k_ident = await derive_k_ident(key_type)
            k_data = await derive_k_data(key_type)
            out_id_part = encode_identity(
                k_ident, ek, key_type, address, app_id, device_id
            )
            out_val_part = encode_content(k_data, ek, key_type, to_counter, new_value)
            new_leaf = (key_type, out_id_part, out_val_part)

        ops.append((ek, old_leaf, new_leaf, proof, w_ek, w_commit))
        leaves.append((ek, key_type, out_id_part, out_val_part))

    # Fold all leaves into one successor root (order-independent, no sort; rejects a
    # duplicate entry_key within the batch). Each proof is against the running root.
    try:
        to_root = compute_batch_root(stored_root, ops)
    except ValueError as e:
        raise DataError(str(e))

    # Root MAC the WM co-signs at finalize, including the canonical empty-root digest.
    mac_key = await derive_mac_key(b"root_mac")
    mac_t = compute_mac(
        mac_key, wallet_id, to_counter.to_bytes(4, "big"), _root_or_empty(to_root)
    )

    # Transition authentication. Roots are folded to their 32-byte MAC-preimage form
    # (EMPTY_ROOT_HASH for empty) and stored in that form, so a verifying device reads
    # exactly what was MAC'd.
    ward_id = await get_ward_id()
    from_root_b = _root_or_empty(stored_root)
    to_root_b = _root_or_empty(to_root)
    k_head = await derive_ward_key(b"K_head")
    k_auth = await derive_ward_key(b"K_auth")
    # FIXME(ward): head_mac is emitted on the ack for an external consumer (the WM, or
    # another device fast-forwarding per design 3.1) but NOTHING verifies it today --
    # the WM emulator keeps auth_commit and ignores this. It is deliberately not
    # persisted (see storage/ward_store.py): re-checking the device's own MAC over its
    # own values would prove nothing. Wire a verifier or drop the field.
    head_mac_v = head_mac(k_head, ward_id, to_counter, to_root)
    auth_commit_v = auth_commit(
        k_auth, ward_id, from_counter, from_root_b, to_counter, to_root_b
    )
    sig = b""
    if WARD_KSIG:
        k_sig = await derive_ward_key(b"K_sig")
        preimage = wm_transition_message(
            ward_id,
            from_counter,
            from_root_b,
            to_counter,
            to_root_b,
            mac_t,
            auth_commit_v,
            head_nonce=ward_head.root_metadata(wallet_id)[1],
        )
        sig = sig_commit(k_sig, preimage)

    ward_store.batch_put(
        wallet_id,
        from_counter,
        to_counter,
        from_root_b,
        to_root_b,
        mac_t if mac_t is not None else _ZERO_MAC,
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

    wallet_id = await get_wallet_id()
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

    ward_id = await get_ward_id()
    if not verify_ward_final(ward_id, to_counter, mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    # Re-verify the transition authorization (F7: AuthCommit binds from->to).
    k_auth = await derive_ward_key(b"K_auth")
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
        await _cache_after_commit(wallet_id, pid, to_counter)
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


# ACCEPTED (trust model): the WM commits a root without evidence that its leaves exist,
# so a host can relay an approved batch to the WM and then withhold the sealed leaves --
# no one can rebuild the trie at that head and the wallet is frozen for every device.
# This one-step, user-confirmed revert is the way out of such a stuck head.
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

    The user confirms on a trusted screen after the AuthCommit verifies and before
    K_sig signs. Stores a BATCH_REVERT envelope and returns `(to_counter, from_root,
    to_root, mac_t, head_mac, auth_revert, sig, ward_id)`."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    if stuck_counter < 1:
        raise DataError("cannot roll back the genesis head")

    wallet_id = await get_wallet_id()
    ward_id = await get_ward_id()

    # The stuck head MUST be exactly the current authenticated head — bind the COUNTER,
    # not just the root (roots are content-addressed and repeat; §2.4/§8.2 point 2).
    cur_counter = ward_store.get_counter(wallet_id)
    _present, cur_root = ward_head.root_get(wallet_id)
    if stuck_counter != cur_counter or _root_or_empty(cur_root) != stuck_root:
        raise DataError("stuck head does not match the current authenticated head")

    # Verify the forward AuthCommit (stuck_counter-1, prev_root) -> (stuck_counter,
    # stuck_root). Its validity proves prev_root is the immediate predecessor and
    # fixes the demotion target — it is not a host-named free-form root (§8.2 point 3).
    k_auth = await derive_ward_key(b"K_auth")
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

    # Only a verified revert reaches the screen; a bogus one fails above without one.
    # Confirmed BEFORE K_sig signs: that signature is what the WM accepts, so signing
    # unasked would let any host undo the user's last approved change.
    await _confirm_revert(stuck_counter)

    to_counter = stuck_counter + 1  # forward-increment (F1), even though root goes back
    to_root = None if prev_root == EMPTY_ROOT_HASH else prev_root

    mac_key = await derive_mac_key(b"root_mac")
    mac_t = compute_mac(
        mac_key, wallet_id, to_counter.to_bytes(4, "big"), _root_or_empty(to_root)
    )

    auth_revert_v = auth_revert(
        k_auth, ward_id, stuck_counter, stuck_root, to_counter, prev_root
    )
    k_head = await derive_ward_key(b"K_head")
    # FIXME(ward): head_mac is emitted on the ack for an external consumer (the WM, or
    # another device fast-forwarding per design 3.1) but NOTHING verifies it today --
    # the WM emulator keeps auth_commit and ignores this. It is deliberately not
    # persisted (see storage/ward_store.py): re-checking the device's own MAC over its
    # own values would prove nothing. Wire a verifier or drop the field.
    head_mac_v = head_mac(k_head, ward_id, to_counter, to_root)
    sig = b""
    if WARD_KSIG:
        k_sig = await derive_ward_key(b"K_sig")
        sig = sig_commit(
            k_sig,
            wm_transition_message(
                ward_id,
                stuck_counter,
                stuck_root,
                to_counter,
                prev_root,
                mac_t,
                auth_revert_v,
                True,
                head_nonce=ward_head.root_metadata(wallet_id)[1],
            ),
        )

    ward_store.batch_put(
        wallet_id,
        stuck_counter,
        to_counter,
        stuck_root,
        prev_root,
        mac_t if mac_t is not None else _ZERO_MAC,
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

    wallet_id = await get_wallet_id()
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

    ward_id = await get_ward_id()
    if not verify_ward_final(ward_id, to_counter, mac, wm_signature):
        raise DataError("WM final attestation verification failed")

    k_auth = await derive_ward_key(b"K_auth")
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
    # FIXME(ward): a revert cannot reach the offline cache -- the device holds only the
    # two roots, not which entries the reverted transition touched -- so cached copies
    # of them stay as they were until a verified lookup or validate_cache corrects them.
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

    wallet_id = await get_wallet_id()
    ward_id = await get_ward_id()
    nonce = random.bytes(ward_head.NONCE_LENGTH)
    ward_head.sync_begin(wallet_id, nonce)

    if __debug__:
        from trezor import log

        log.debug(__name__, "sync: minted nonce for wallet_id=%s", wallet_id)

    return nonce, _WARD_VERSION, wallet_id, ward_id


# Outcome of the OPTIONAL label-freshness check (`label_freshness`). The host decides
# whether to ask the WM: an unchecked label is shown exactly as before.
FRESH_UNCHECKED = const(0)  # no attestation attached
FRESH_CURRENT = const(1)  # the WM's head is this device's own (counter, root)
FRESH_BEHIND = const(2)  # the WM's head is ahead: the label may be outdated
FRESH_INVALID = const(3)  # attached, but forged, stale, or naming another root


async def label_freshness(nonce: bytes, attestation) -> int:
    """Judge whether the root a label was just verified against is still the WM's
    current head, from an attestation the host chose to attach to the proof.

    `attestation` is `(counter, mac, wm_signature, timestamp, head_nonce)` over
    `nonce`, the device-minted nonce of this very proof request, or None. The checks
    mirror `ingest`, but NOTHING is installed: a label pull must never move the
    device's state, so a host gains no new way to change it by answering one.

    An equal counter with a different MAC is a fork, not freshness, and reads as
    invalid; a counter below the device's floor likewise."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor import utils

    if attestation is None:
        return FRESH_UNCHECKED
    counter, mac_msg, signature, timestamp, head_nonce = attestation
    mac = mac_msg if mac_msg is not None else _ZERO_MAC
    if (
        len(mac) != 32
        or len(head_nonce) != 32
        or timestamp <= 0
        or timestamp >= 1 << 63
        or (counter > 0 and mac == _ZERO_MAC)
    ):
        return FRESH_INVALID

    wallet_id = await get_wallet_id()
    ward_id = await get_ward_id()
    if not verify_wm_attestation(
        ward_id, nonce, counter, mac, signature, timestamp, head_nonce
    ):
        return FRESH_INVALID
    if timestamp + 300 < ward_head.root_metadata(wallet_id)[0]:
        return FRESH_INVALID

    floor = ward_store.get_counter(wallet_id)
    if counter < floor:
        return FRESH_INVALID
    if counter > floor:
        return FRESH_BEHIND

    present, root = ward_head.root_get(wallet_id)
    if not present:
        return FRESH_BEHIND
    if counter == 0 and root is None:
        expected = _ZERO_MAC
    else:
        mac_key = await derive_mac_key(b"root_mac")
        expected = compute_mac(
            mac_key, wallet_id, counter.to_bytes(4, "big"), _root_or_empty(root)
        )
    return FRESH_CURRENT if utils.consteq(expected, mac) else FRESH_INVALID


async def ingest(
    counter: int,
    mac_msg: bytes | None,
    wm_signature: bytes,
    timestamp: int,
    head_nonce: bytes,
) -> tuple[int, bytes]:
    """Verify + record the WM freshness attestation for the open sync round.
    Returns (counter, wallet_id)."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await get_wallet_id()

    ctx = ward_head.sync_get(wallet_id)
    if ctx is None:
        raise DataError("no sync round in progress")
    nonce, _state, _counter, _mac = ctx

    ward_id = await get_ward_id()
    mac = mac_msg if mac_msg is not None else _ZERO_MAC
    if counter > 0 and mac == _ZERO_MAC:
        raise DataError("positive counter requires an authenticated wallet MAC")
    if len(head_nonce) != 32 or timestamp <= 0 or timestamp >= 1 << 63:
        raise DataError("invalid attestation metadata")
    if timestamp + 300 < ward_head.root_metadata(wallet_id)[0]:
        raise DataError("WM timestamp regressed")
    if not verify_wm_attestation(
        ward_id, nonce, counter, mac, wm_signature, timestamp, head_nonce
    ):
        raise DataError("WM attestation verification failed")

    # Anti-rollback: the attested counter cannot precede the device's floor.
    if counter < ward_store.get_counter(wallet_id):
        raise DataError("attested counter is older than counter_loc")

    ward_head.sync_set_attested(wallet_id, counter, mac_msg, timestamp, head_nonce)

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
    (counter, new_root, wallet_id, root_mac).

    Only for a device with NO anchor yet (counter_loc == 0), or to re-establish the
    root at the anchored counter itself. Moving an anchored device FORWARD goes
    through `verify_chain`: a MAC-matching root proves only that some device of this
    wallet computed it, not that it descends from this device's anchor, so accepting
    it here would let a host move the device onto a fork and make the chain check
    optional."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await get_wallet_id()

    ctx = ward_head.sync_get(wallet_id)
    if ctx is None or ctx[1] != ward_head.SYNC_ATTESTED:
        raise DataError("no attested sync round to merge")
    _nonce, _state, counter_ext, mac_ext = ctx

    floor = ward_store.get_counter(wallet_id)
    if floor != 0 and counter_ext != floor:
        raise DataError("an anchored device advances only through WARDVerifyChain")

    if mac_ext is None:
        # Attested empty tree: the supplied root must be absent too.
        if root is not None or counter_ext != 0:
            raise DataError("attested tree is empty but a root was supplied")
    else:
        if root is not None and len(root) != ward_store.ROOT_LENGTH:
            raise DataError("root must be exactly 32 bytes")
        mac_key = await derive_mac_key(b"root_mac")
        computed = compute_mac(
            mac_key, wallet_id, counter_ext.to_bytes(4, "big"), _root_or_empty(root)
        )
        if computed != mac_ext:
            raise DataError("root does not match the attested mac")

    present, current = ward_head.root_get(wallet_id)
    if present and counter_ext == floor and root != current:
        raise DataError("one counter cannot identify two roots")

    timestamp, head_nonce = ward_head.sync_metadata(wallet_id)
    timestamp = max(timestamp, ward_head.root_metadata(wallet_id)[0])
    ward_head.root_set(wallet_id, root, timestamp, head_nonce)
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

    wallet_id = await get_wallet_id()
    ctx = ward_head.sync_get(wallet_id)
    if ctx is None or ctx[1] != ward_head.SYNC_ATTESTED:
        raise DataError("no attested sync round to verify against")
    _nonce, _state, counter_ext, mac_ext = ctx

    ward_id = await get_ward_id()
    k_auth = await derive_ward_key(b"K_auth")

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
        # The wallet HMAC authenticates links on-device; WM verifies the public signature.

    # The authorized chain must land EXACTLY on the WM-attested head.
    if running_counter != counter_ext:
        raise DataError("chain does not terminate at the attested counter")
    root_head = None if running_root == EMPTY_ROOT_HASH else running_root
    if mac_ext is None:
        if root_head is not None or counter_ext != 0:
            raise DataError("unauthenticated empty chain head")
    else:
        mac_key = await derive_mac_key(b"root_mac")
        computed = compute_mac(
            mac_key,
            wallet_id,
            counter_ext.to_bytes(4, "big"),
            _root_or_empty(root_head),
        )
        if computed != mac_ext:
            raise DataError("chain terminal root does not match the attested mac")

    timestamp, head_nonce = ward_head.sync_metadata(wallet_id)
    timestamp = max(timestamp, ward_head.root_metadata(wallet_id)[0])
    ward_head.root_set(wallet_id, root_head, timestamp, head_nonce)
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


async def _show_entry(
    index: int, app_id: bytes, identifier: bytes, value: bytes
) -> bool:
    """One verified entry on a trusted screen. Returns False if the user stops the
    listing there."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import ActionCancelled

    try:
        await confirm_properties(
            "ward_list_entry",
            "WARD entry " + str(index),
            [
                display_property("Domain", app_id, False),
                display_property("Key", identifier),
                display_property("Value", value),
            ],
            br_code=ButtonRequestType.Other,
            verb="Next",
        )
    except ActionCancelled:
        return False
    return True


async def list_entries(
    fetch,
    app_id: str | None = None,
    key_type: str | None = None,
    device_id: int | None = None,
) -> tuple[int, int, int, bool]:
    """Show every entry under the authenticated root that matches the filters, one per
    trusted screen, via a verified top-down walk (`trie.TrieWalk`).

    `fetch(node_hash)` returns the host's nodes for that hash in pre-order, each
    `(split_bit, left, right, entry_key, (key_type, id_part), val_part)`; a set
    entry_key marks a leaf. Nothing a node claims is used before the walk has
    verified it against a hash already trusted.

    Every leaf is verified, filtered or not -- skipping one would let the host hide
    a matching entry behind it. Of the ones shown, the identity is checked to be the
    preimage of the leaf's entry_key: the walk only proves the leaf is in the trie,
    and the screen names the entry by what the identity says.

    Returns `(shown, entries, counter, complete)`: counts only, so the host learns
    nothing it did not already hold. `complete` is False if the user stopped early.
    Read-only: no device state changes."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    wallet_id = await get_wallet_id()
    present, root = ward_head.root_get(wallet_id)
    if not present:
        raise DataError("no authenticated root in session")
    counter = ward_store.get_counter(wallet_id)
    app_filter = None if app_id is None else app_id.encode()

    k_path = await derive_k_path()
    keys = {}  # key_type -> (K_ident, K_data), derived once per type
    walk = TrieWalk(root)
    shown = 0
    entries = 0
    while walk.expected() is not None:
        nodes = await fetch(walk.expected())
        if not nodes:
            raise DataError("WARD listing: the host returned no node")
        for split_bit, left, right, ek, identity, val_part in nodes:
            if walk.expected() is None:
                raise DataError("WARD listing: nodes past the end of the trie")
            kt, id_part = identity
            try:
                if ek is None:
                    walk.branch(split_bit or 0, left or b"", right or b"")
                    continue
                kt = kt or ENTRY_TYPE_ADDRESS
                if id_part is None or val_part is None:
                    raise ValueError("leaf is missing a part")
                walk.leaf(ek, commit_of(kt, id_part, val_part))
            except ValueError as e:
                raise DataError("WARD listing: " + str(e))
            entries += 1
            if key_type is not None and kt != key_type:
                continue

            if kt not in keys:
                keys[kt] = (await derive_k_ident(kt), await derive_k_data(kt))
            k_ident, k_data = keys[kt]
            try:
                identifier, leaf_app, leaf_device = decode_identity(
                    k_ident, ek, kt, id_part
                )
                if entry_key(k_path, leaf_app, identifier, kt, leaf_device) != ek:
                    raise ValueError("leaf identity does not match its path")
                if app_filter is not None and bytes(leaf_app) != app_filter:
                    continue
                if device_id is not None and leaf_device != device_id:
                    continue
                _c_leaf, value = decode_content(k_data, ek, kt, val_part)
            except ValueError as e:
                raise DataError("WARD listing: " + str(e))

            shown += 1
            if not await _show_entry(shown, leaf_app, identifier, value):
                return shown, entries, counter, False

    if __debug__:
        from trezor import log

        log.debug(__name__, "list_entries: shown=%d of %d entries", shown, entries)
    return shown, entries, counter, True


def _require_offline_store() -> None:
    from trezor import utils
    from trezor.wire import DataError

    if not utils.USE_WARD:
        raise DataError("WARD cache: this firmware has no offline store")


async def _verified_leaf(ek: bytes, kt: str, id_part, val_part, proof, root) -> tuple:
    """Verify the leaf (kt, id_part, val_part) is a MEMBER at `ek` under `root`, and
    open it: (identifier, app_id, device_id, C_leaf, value). The identity must be the
    preimage of `ek`, so the entry is named by what its path was derived from, never by
    what a sealed identity merely claims. Raises DataError otherwise."""
    from trezor.wire import DataError

    try:
        if not verify_proof(ek, kt, id_part, val_part, proof, root):
            raise ValueError("membership proof does not verify")
        identifier, app_id, device_id = decode_identity(
            await derive_k_ident(kt), ek, kt, id_part
        )
        if entry_key(await derive_k_path(), app_id, identifier, kt, device_id) != ek:
            raise ValueError("leaf identity does not match its path")
        c_leaf, value = decode_content(await derive_k_data(kt), ek, kt, val_part)
    except ValueError as e:
        raise DataError("WARD cache: " + str(e))
    return identifier, bytes(app_id), device_id, c_leaf, value


async def _put_record(store, key: bytes, raw: bytes) -> None:
    from trezor.wire import DataError

    from .store import WardError

    try:
        await store.set(key, raw)
    except WardError:
        raise DataError("WARD cache: the offline store refused the entry")


async def _confirm_sticky(app_id: bytes, identifier: bytes, value: bytes) -> None:
    """Trusted confirmation before an entry becomes STICKY. Raises ActionCancelled if
    the user rejects."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "ward_sticky",
        "Keep WARD entry offline",
        [
            display_property("Domain", app_id, False),
            display_property("Key", identifier),
            display_property("Value", value),
            ("Note", "It is shown, marked cached, while no host can verify it.", False),
        ],
        br_code=ButtonRequestType.ProtectCall,
    )


async def _cache_after_commit(wallet_id: bytes, pid: int, counter: int) -> None:
    """Bring this device's cached copy of a just-COMMITTED intent in line with it: the
    user approved this exact write here, so the copy is updated to the new value (at
    C_leaf = the transition counter, sticky bit kept) or removed for a delete -- without
    waiting for a host-served proof. Never fails the commit: a copy that cannot be
    updated is removed rather than left stale."""
    import storage.ward_store as ward_store
    from trezor import utils
    from trezor.wire import DataError

    from . import cache

    if not utils.USE_WARD:
        return
    rec = ward_store.queue_get(wallet_id, pid)
    if rec is None:
        return
    _c, _s, address, new_value, _r, _m, app_id, kt, device_id = rec
    try:
        store = await cache.store_for(app_id)
    except DataError:
        return
    key = cache.record_key(kt.decode() if kt else ENTRY_TYPE_ADDRESS, device_id, address)
    raw = await store.get(key)
    if raw is None:
        return
    if ward_store.queue_is_delete(wallet_id, pid):
        await store.delete(key)
        return
    flags = cache.parse_value(raw)[0]
    try:
        await _put_record(store, key, cache.record_value(flags, counter, new_value))
    except DataError:
        await store.delete(key)


async def _show_sticky_change(
    app_id: bytes, identifier: bytes, cached: bytes, ward_value: bytes | None
) -> None:
    """Tell the user, before it happens, that a verified answer changes a STICKY copy
    they chose to keep offline: WARD has another value (`ward_value`), or no longer has
    the entry (None). Acknowledgement only -- the change goes ahead either way.
    FIXME(ward, TBD): let the user keep the cached copy instead of updating it."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import ActionCancelled

    props = [
        display_property("Domain", app_id, False),
        display_property("Key", identifier),
        display_property("Cached value", cached),
    ]
    if ward_value is None:
        title = "Offline entry removed"
        props.append(("Note", "WARD no longer has this entry.", False))
    else:
        title = "Offline entry changed"
        props.append(display_property("WARD value", ward_value))
    try:
        await confirm_properties(
            "ward_sticky_changed",
            title,
            props,
            br_code=ButtonRequestType.Warning,
            verb="Continue",
        )
    except ActionCancelled:
        pass


async def cache_entry(
    ek: bytes,
    key_type: str | None,
    id_part,
    val_part,
    proof: list[bytes],
    witnessed: bool,
    sticky: bool = False,
) -> tuple[bool, int]:
    """Copy the trie entry at `ek` into the offline cache of the app it belongs to.

    The host names the entry only by its entry_key and serves the leaf; the device:
      1. requires a MEMBERSHIP proof of that leaf under its authenticated root -- a
         non-membership answer or a proof that does not verify stores nothing;
      2. decrypts the identity and checks it is the preimage of `ek`, so the record is
         filed under the identifier and domain the path was derived from;
      3. stores it in that domain's cache store (`cache`), with the leaf's C_leaf, and
         STICKY if asked -- or if the cached copy already was: stickiness is only ever
         added here, never dropped.

    No screen for a plain copy: `ek` binds the domain, and the leaf is in the trie only
    because the user approved writing it for that domain. Making it STICKY is the user's
    decision and is confirmed on screen (`_confirm_sticky`); stickiness lives only in this
    device's cache record, never in the leaf. A domain with no WardApp is refused.
    Returns (replaced, counter); nothing of the entry goes back to the host.

    KNOWN: the offline store is small (32 records / 8 KiB) and shared by every app and
    passphrase wallet, and nothing is evicted, so a host can fill it with plain copies."""
    import storage.ward_head as ward_head
    import storage.ward_store as ward_store
    from trezor.wire import DataError

    from . import cache

    _require_offline_store()
    wallet_id = await get_wallet_id()
    present, root = ward_head.root_get(wallet_id)
    if not present:
        raise DataError("no authenticated root in session")
    if len(ek) != 32:
        raise DataError("entry_key must be 32 bytes")
    if root is None or witnessed or id_part is None or val_part is None:
        raise DataError("WARD entry is not in the trie")
    kt = key_type or ENTRY_TYPE_ADDRESS
    identifier, app_id, device_id, c_leaf, value = await _verified_leaf(
        ek, kt, id_part, val_part, proof, root
    )

    store = await cache.store_for(app_id)
    key = cache.record_key(kt, device_id, identifier)
    old = await store.get(key)
    flags = 0 if old is None else cache.parse_value(old)[0] & cache.FLAG_STICKY
    if sticky and not flags:
        # Stickiness is the user's decision: a sticky entry is shown (as cached) even
        # while no proof can be had, so the host may not grant it on its own.
        await _confirm_sticky(app_id, identifier, value)
        flags = cache.FLAG_STICKY
    await _put_record(store, key, cache.record_value(flags, c_leaf, value))

    if __debug__:
        from trezor import log

        log.debug(__name__, "cache_entry: stored, replaced=%s", old is not None)
    return old is not None, ward_store.get_counter(wallet_id)


async def export_cache() -> list[bytes]:
    """Back up every cached WARD entry of the active wallet: one blob per entry,
    sealed so that only a device unlocked with this same wallet can open it -- the host
    that carries the backup learns nothing from it and cannot forge one. Read-only."""
    from . import cache

    _require_offline_store()
    blobs = []
    for domain, key, value in await cache.records():
        blobs.append(await cache.seal(domain, key, value))
    return blobs


async def import_cache(blobs: list[bytes], pull) -> tuple[int, int]:
    """Load backed-up entries (from `export_cache` on any device of this wallet) into
    the offline cache. Every blob is opened first -- one this wallet did not seal fails
    the whole import before anything is stored -- and every entry is then CHECKED against
    the device's authenticated root with a proof the device pulls (`pull(entry_key)`, as
    in `validate_cache`; sync first):

      in WARD      stored with WARD's current value and C_leaf (not the blob's), keeping
                   the blob's sticky bit
      absent       skipped -- so replaying an old backup cannot bring back an entry WARD
                   deleted

    A proof that does not verify, or a host that cannot serve one, fails the import. An
    entry never replaces a NEWER cached copy (higher C_leaf). If any entry would become
    sticky here, the user confirms the import once on screen. Returns (imported,
    skipped)."""
    import storage.ward_head as ward_head
    from trezor.wire import DataError

    from . import cache

    _require_offline_store()
    opened = []  # every blob is opened before anything is stored
    for blob in blobs:
        opened.append(await cache.open_blob(blob))

    wallet_id = await get_wallet_id()
    present, root = ward_head.root_get(wallet_id)
    if not present:
        raise DataError("no authenticated root in session")
    k_path = await derive_k_path()

    planned = []  # (store, key, flags, c_leaf, value, becomes_sticky)
    skipped = 0
    for domain, key, raw in opened:
        flags, _blob_c, _blob_value = cache.parse_value(raw)
        kt, device_id, identifier = cache.parse_key(key)
        ek = entry_key(k_path, domain, identifier, kt, device_id)
        a_kt, id_part, val_part, proof, w_ek, w_commit = await pull(ek)
        if root is not None and w_ek is None and val_part is not None:
            if a_kt and a_kt != kt:
                raise DataError("WARD cache: proof is for another key type")
            _i, _a, _d, c_leaf, value = await _verified_leaf(
                ek, kt, id_part, val_part, proof, root
            )
        else:
            if root is not None:
                if w_ek is None or w_commit is None:
                    raise DataError("WARD cache: no proof of absence")
                if not verify_nonmembership(ek, w_ek, w_commit, proof, root):
                    raise DataError("WARD cache: proof of absence does not verify")
            skipped += 1
            continue
        store = await cache.store_for(domain)
        old = await store.get(key)
        old_flags = 0
        if old is not None:
            old_flags, old_c, old_value = cache.parse_value(old)
            if old_c > c_leaf:
                skipped += 1
                continue
            if old_flags & cache.FLAG_STICKY and old_value != value:
                await _show_sticky_change(domain, identifier, old_value, value)
        sticky = (flags | old_flags) & cache.FLAG_STICKY
        newly_sticky = sticky and not old_flags & cache.FLAG_STICKY
        planned.append((store, key, sticky, c_leaf, value, newly_sticky))

    new_sticky = sum(1 for p in planned if p[5])
    if new_sticky:
        await _confirm_import_sticky(len(planned), new_sticky)
    for store, key, sticky, c_leaf, value, _new in planned:
        await _put_record(store, key, cache.record_value(sticky, c_leaf, value))
    return len(planned), skipped


async def _confirm_import_sticky(entries: int, sticky: int) -> None:
    """Trusted confirmation before an import makes entries STICKY on this device."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "ward_import_sticky",
        "Load WARD backup",
        [
            ("Entries", str(entries), False),
            ("Kept offline", str(sticky), False),
            ("Note", "Offline entries are shown, marked cached, without a host.", False),
        ],
        br_code=ButtonRequestType.ProtectCall,
    )


async def cached_label(domain, identifier: bytes) -> bytes | None:
    """Offline fallback for a label lookup the host could not serve: the value of a
    STICKY cached entry of `domain` (a WardCaller), or None. Not verified -- no proof
    could be had -- so it is shown as cached, not as proven.

    THREAT MODEL (accepted, known DoS from the host/Suite side): a host can always
    claim to be unavailable instead of serving a proof (and a failing wardd is reported
    the same way), and so keep a sticky entry in use after ANOTHER device deleted it in
    WARD; the label is marked cached. The host does learn which entries are cached
    (validate_cache pulls a proof per cached entry), but it cannot make an entry sticky
    (the user confirms that), cannot bring a deleted one back from a backup (import is
    checked against WARD), and this device's own deletes and updates reach its cache
    when they are committed (`_cache_after_commit`)."""
    from trezor import utils
    from trezor.wire import DataError

    from . import cache

    if not utils.USE_WARD:
        return None
    try:
        store = await cache.store_for(domain.app_id)
    except DataError:
        return None
    raw = await store.get(cache.record_key(ENTRY_TYPE_ADDRESS, 0, identifier))
    if raw is None:
        return None
    flags, _c_leaf, value = cache.parse_value(raw)
    return value if flags & cache.FLAG_STICKY else None


async def refresh_cached_label(
    domain, identifier: bytes, status: str, val_part
) -> None:
    """After a label lookup the device VERIFIED (status "membership" or
    "non-membership"), bring the cached copy of that entry, if any, in line with WARD:
    update it to the proven value, or remove it when WARD proved it absent -- sticky or
    not. Any other status changes nothing. A change to a STICKY copy is shown to the
    user first (`_show_sticky_change`)."""
    from trezor import utils
    from trezor.wire import DataError

    from . import cache

    if not utils.USE_WARD or status not in ("membership", "non-membership"):
        return
    try:
        store = await cache.store_for(domain.app_id)
    except DataError:
        return
    key = cache.record_key(ENTRY_TYPE_ADDRESS, 0, identifier)
    raw = await store.get(key)
    if raw is None:
        return
    flags, old_c, old_value = cache.parse_value(raw)
    sticky = flags & cache.FLAG_STICKY
    if status == "non-membership":
        if sticky:
            await _show_sticky_change(domain.app_id, identifier, old_value, None)
        await store.delete(key)
        return
    ek = entry_key(await derive_k_path(), domain.app_id, identifier)
    c_leaf, value = decode_content(
        await derive_k_data(ENTRY_TYPE_ADDRESS), ek, ENTRY_TYPE_ADDRESS, val_part
    )
    # FIXME(ward, TBD): the user is told (sticky copies) but not asked -- the copy is
    # updated either way. Also unresolved: a proof against a root OLDER than the copy
    # (old_c above the device counter) currently downgrades or removes it.
    if sticky and value != old_value:
        await _show_sticky_change(domain.app_id, identifier, old_value, value)
    if (c_leaf, value) != (old_c, old_value):
        await _put_record(store, key, cache.record_value(flags, c_leaf, value))


async def validate_cache(pull) -> tuple[int, int, int, int]:
    """Check every cached WARD entry against the authenticated root (run it after a
    sync), pulling one proof per entry -- `pull(entry_key)` returns the host's
    (key_type, id_part, val_part, proof, witness_entry_key, witness_commit). Every
    verdict rests on a verified proof; a proof that does not verify aborts the run with
    DataError and changes nothing further.

      in WARD, same value       unchanged
      in WARD, other value      updated to WARD's value
      absent from WARD          removed -- sticky entries too: stickiness only lets an
                                entry be used while NO proof can be had (`cached_label`)

    Every change to a STICKY copy is shown to the user first (`_show_sticky_change`).

    Returns (checked, unchanged, updated, removed) -- counts only."""
    import storage.ward_head as ward_head
    from trezor.wire import DataError

    from . import cache

    _require_offline_store()
    wallet_id = await get_wallet_id()
    present, root = ward_head.root_get(wallet_id)
    if not present:
        raise DataError("no authenticated root in session")
    k_path = await derive_k_path()

    checked = unchanged = updated = removed = 0
    for domain, key, raw in await cache.records():
        kt, device_id, identifier = cache.parse_key(key)
        flags, c_leaf, value = cache.parse_value(raw)
        ek = entry_key(k_path, domain, identifier, kt, device_id)
        a_kt, id_part, val_part, proof, w_ek, w_commit = await pull(ek)
        checked += 1
        store = await cache.store_for(domain)

        if root is not None and w_ek is None and val_part is not None:
            if a_kt and a_kt != kt:
                raise DataError("WARD cache: proof is for another key type")
            _ident, _app, _dev, new_c, new_value = await _verified_leaf(
                ek, kt, id_part, val_part, proof, root
            )
            # FIXME(ward, TBD): same policy question as refresh_cached_label --
            # the user is told about a sticky copy but not asked; and no guard yet
            # against a root older than the cached copy.
            if new_value == value and new_c == c_leaf:
                unchanged += 1
                continue
            if flags & cache.FLAG_STICKY and new_value != value:
                await _show_sticky_change(domain, identifier, value, new_value)
            await _put_record(store, key, cache.record_value(flags, new_c, new_value))
            updated += 1
            continue

        if root is not None:
            if w_ek is None or w_commit is None:
                raise DataError("WARD cache: no proof of absence")
            if not verify_nonmembership(ek, w_ek, w_commit, proof, root):
                raise DataError("WARD cache: proof of absence does not verify")
        if flags & cache.FLAG_STICKY:
            await _show_sticky_change(domain, identifier, value, None)
        await store.delete(key)
        removed += 1

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "validate_cache: checked=%d unchanged=%d updated=%d removed=%d",
            checked,
            unchanged,
            updated,
            removed,
        )
    return checked, unchanged, updated, removed


async def pending() -> tuple[list[int], list[bytes], bytes, bytes]:
    """Return (pending_ids, addresses, wallet_id, ward_id) for every queued
    candidate of the active wallet, in allocation order (the two lists are
    parallel). ward_id lets a host resolve the WM-facing anchor up front."""
    import storage.ward_store as ward_store

    wallet_id = await get_wallet_id()
    ward_id = await get_ward_id()

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

    wallet_id = await get_wallet_id()
    counter = ward_store.bump_counter(wallet_id)
    ward_head.root_set(wallet_id, root)

    mac_key = await derive_mac_key(b"root_mac")
    new_root = root
    root_mac = (
        compute_mac(mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )

    return counter, new_root, wallet_id, root_mac
