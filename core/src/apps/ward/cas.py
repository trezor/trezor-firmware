"""CAS: authorising a transition from one root to the next. The ONLY authority on state.

    preimage   = len8(tag) || tag || ward_id || from_counter(4B BE) || from_root(32B)
                                             || to_counter(4B BE)   || to_root(32B)
    AuthCommit = HMAC-SHA256(K_auth, preimage)

`tag` is TAG_COMMIT for a write and TAG_REVERT for a rollback; an empty tree is EMPTY_ROOT.

A MAC, because exactly the seed holders (this wallet's devices) need to verify it. The WM,
which arbitrates ordering, gets its own authenticator over the same bytes plus its head nonce
(`wm_sig`, Ed25519 under K_sig, bottom of this file). The WM sees roots and could attest one
the wallet never held; descent through K_auth links (`verify_chain`) is what catches that.

A chain of links from a trusted baseline proves descent (contiguous ends, forward steps of at
most MAX_BATCH, each authorised), not currency -- the WM attestation supplies that.
"""

from micropython import const

# The most changes one transition (a batch) may carry; every step rule is
# "1 <= to - from <= MAX_BATCH". Variable steps mean every walk must land EXACTLY.
MAX_BATCH = const(8)

TAG_COMMIT = b"WARD COMMIT v3"
TAG_REVERT = b"WARD REVERT v3"

# The WM's own authorisations: `transition_preimage` plus the head nonce (`wm_preimage`).
TAG_WM_HEAD = b"WARD WM COMMIT v3"
TAG_WM_INIT = b"WARD WM INIT v3"
# Lets a WM apply policy to demotions; replay protection is the head nonce's job.
TAG_WM_REVERT = b"WARD WM REVERT v3"


def transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
) -> bytes:
    """The bytes a transition is authorised over -- ONE builder for both authenticators.

    Both ends are named, so a link cannot be replayed after a different predecessor, and every
    operand the WM acts on is inside the bytes it verifies. The head nonce is NOT here: a
    device walking the chain holds no WM state.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if len(ward_id) != 32 or len(from_root) != 32 or len(to_root) != 32:
        raise DataError("WARD: transition operands must be 32 bytes")

    # Length-prefixed tag: tags differ in length, so no cross-domain collision.
    return (
        bytes([len(tag)])
        + tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + from_root
        + to_counter.to_bytes(4, "big")
        + to_root
    )


def auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    tag: bytes = TAG_COMMIT,
) -> bytes:
    """Authorise a transition. Only a device holding the seed can produce this."""
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256,
        k_auth,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root),
    ).digest()


def verify_auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    mac: bytes,
    tag: bytes = TAG_COMMIT,
) -> bool:
    """Was this exact transition authorised by a holder of this wallet's K_auth?"""
    from trezor.utils import consteq

    expected = auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, tag
    )
    # CONSTANT TIME: `mac` comes from the host, and bytes `==` short-circuits.
    return consteq(expected, mac)


def _link_is_revert(k_auth: bytes, ward_id: bytes, link: "tuple") -> bool:
    """Is this link a REVERT (True) or a COMMIT (False)? Raises if it is neither.

    Both kinds are real transitions for descent; which one it was is reported, not swallowed.
    """
    from trezor.wire import DataError

    from_counter, from_root, to_counter, to_root, mac = link
    for tag, is_revert in ((TAG_COMMIT, False), (TAG_REVERT, True)):
        if verify_auth_commit(
            k_auth, ward_id, from_counter, from_root, to_counter, to_root, mac, tag
        ):
            return is_revert
    raise DataError("WARD: chain link is not authorised")


def verify_chain_step(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: bytes | None,
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
    """Fold one link (from_counter, from_root, to_counter, to_root, auth_commit) FORWARD.

    Its `from` must be the running head and it must advance by 1..MAX_BATCH, before the MAC is
    checked. Returns `(to_counter, to_root, is_revert)`; raises on any failure.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_counter, from_root, to_counter, to_root, _mac = link

    if from_counter != running_counter:
        raise DataError("WARD: chain link does not follow the running counter")
    if root_or_empty(from_root) != root_or_empty(running_root):
        raise DataError("WARD: chain link does not follow the running root")
    if not 1 <= to_counter - running_counter <= MAX_BATCH:
        raise DataError("WARD: chain link must advance the counter by 1 to MAX_BATCH")

    return to_counter, to_root, _link_is_revert(k_auth, ward_id, link)


def verify_chain_step_back(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: "bytes | None",
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
    """Fold one link BACKWARD off the running head; returns its predecessor and `is_revert`.

    A separate function, not a flag: which end is pinned is the whole security of a walk.
    Backwards the `to` end is pinned by an already-established state, so an orphaned link the
    WM never accepted is refused on the root check before its MAC is computed.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_counter, from_root, to_counter, to_root, _mac = link

    if to_counter != running_counter:
        raise DataError("WARD: chain link does not end at the running counter")
    if root_or_empty(to_root) != root_or_empty(running_root):
        raise DataError("WARD: chain link does not end at the running root")
    # A batch steps back by several; the calling walk must land EXACTLY on its stop counter.
    if not 1 <= running_counter - from_counter <= MAX_BATCH:
        raise DataError("WARD: chain link must step the counter back by 1 to MAX_BATCH")

    return from_counter, from_root, _link_is_revert(k_auth, ward_id, link)


# --- the queued INTENT ---------------------------------------------------------------------
#
# A queued change exported for backup comes back as host-held material; this MAC under K_auth
# lets the device recognise its own intent. It binds the identity (a queued change has no path
# yet), not a counter: a restored change comes back with none assigned.

TAG_INTENT = b"WARD INTENT v1"

OP_SET = 1  # queue a value at a path; there is no delete intent yet


def intent_preimage(
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
) -> bytes:
    """The bytes a queued intent is authenticated over: wallet, op, identity AND value.

    Length-prefixed fields. A wire contract, deliberately separate from the flash encoding
    in `offline_store.encode_record`.
    """
    from trezor.wire import DataError

    kt = key_type.encode()
    ai = app_id.encode()
    if len(ward_id) != 32:
        raise DataError("WARD: intent operands must be 32 bytes")
    if len(kt) > 0xFF or len(ai) > 0xFF:
        raise DataError("WARD: key_type or app_id too long to authenticate")
    if len(identifier) > 0xFFFF or len(value) > 0xFFFF:
        raise DataError("WARD: identifier or value too long to authenticate")

    return (
        TAG_INTENT
        + ward_id
        + bytes([op])
        + bytes([len(kt)])
        + kt
        + bytes([len(ai)])
        + ai
        + len(identifier).to_bytes(2, "big")
        + identifier
        + len(value).to_bytes(2, "big")
        + value
    )


def intent_mac(
    k_auth: bytes,
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
) -> bytes:
    """Authenticate a queued intent. Only a device holding the seed can produce this."""
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256,
        k_auth,
        intent_preimage(ward_id, op, key_type, app_id, identifier, value),
    ).digest()


def verify_intent_mac(
    k_auth: bytes,
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    mac: bytes,
) -> bool:
    """Did a device of this wallet queue EXACTLY this intent? (Not: should it be queued again.)"""
    from trezor.utils import consteq

    # Constant time, as in `verify_auth_commit`.
    expected = intent_mac(k_auth, ward_id, op, key_type, app_id, identifier, value)
    return consteq(expected, mac)


# --- the WM's authorisation -------------------------------------------------------------
#
# Ed25519 under K_sig over `transition_preimage` + the WM's head nonce, so only a device of this
# wallet can advance the WM head (`ward_id` is the public key). Not redundant with `auth_commit`:
# the verifier sets are disjoint.
#
# THE HEAD NONCE. The WM's state is `(counter, root, head_nonce)` and every accepted transition
# rotates the nonce, so one `wm_sig` moves the head at most once even though `(counter, root)`
# pairs recur (roots are content-addressed; a revert re-creates an old one). The device learns
# the nonce only from a WM-signed attestation.
#
# WM OBLIGATION, unenforceable by the device: a superseded nonce must NEVER become current again
# -- not by rotation, failover, or backup restore. Restoring one revives every authorisation
# minted against it.

NO_HEAD_NONCE = b"\x00" * 32
"""The nonce `head_init_sig` is minted under; NEVER a live head nonce.

The WM draws a real nonce on enrolment, so a replayed enrolment cannot recreate the genesis
predecessor `(0, EMPTY_ROOT, NO_HEAD_NONCE)` a first write was authorised against.
`adopt.verify_round_attestation` refuses attested heads carrying it.
"""


def wm_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
    head_nonce: bytes,
) -> bytes:
    """`transition_preimage` with the fixed-width head nonce appended."""
    from trezor.wire import DataError

    if len(head_nonce) != 32:
        raise DataError("WARD: the WM head nonce must be 32 bytes")
    return (
        transition_preimage(
            tag, ward_id, from_counter, from_root, to_counter, to_root
        )
        + head_nonce
    )


def wm_sig(
    k_sig: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    head_nonce: bytes,
    tag: bytes = TAG_WM_HEAD,
) -> bytes:
    """Authorise a head advance to the WM (TAG_WM_HEAD, or TAG_WM_REVERT for a demotion)."""
    from trezor.crypto.curve import ed25519

    return ed25519.sign(
        k_sig,
        wm_preimage(
            tag, ward_id, from_counter, from_root, to_counter, to_root, head_nonce
        ),
    )


async def authorise(
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    revert: bool = False,
) -> "tuple[bytes, bytes]":
    """`(auth_commit, wm_sig)` for one transition: the device-facing MAC and the WM-facing
    signature over the same step, the latter bound to the WM head nonce this session attested.
    Every minting path goes through here, so the two can never name different transitions."""
    from . import round as sync_round
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id

    ward_id = await derive_ward_id()
    ops = (ward_id, from_counter, from_root, to_counter, to_root)
    return (
        auth_commit(await derive_k_auth(), *ops, TAG_REVERT if revert else TAG_COMMIT),
        wm_sig(
            await derive_k_sig(),
            *ops,
            sync_round.require_head_nonce(),
            TAG_WM_REVERT if revert else TAG_WM_HEAD,
        ),
    )


def _wm_verify(ward_id: bytes, signature: bytes, *preimage_args) -> bool:
    """Ed25519-verify `wm_preimage(*preimage_args)` under `ward_id`; any failure is False."""
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    try:
        return ed25519.verify(ward_id, signature, wm_preimage(*preimage_args))
    except Exception:
        return False


def verify_wm_sig(
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    head_nonce: bytes,
    signature: bytes,
    tag: bytes = TAG_WM_HEAD,
) -> bool:
    """What the WM checks, against its OWN current nonce. On the device only for tests."""
    return _wm_verify(
        ward_id,
        signature,
        tag, ward_id, from_counter, from_root, to_counter, to_root, head_nonce,
    )


def head_init_sig(
    k_sig: bytes, ward_id: bytes, counter: int, root: bytes | None
) -> bytes:
    """Authorise the FIRST head a WM holds for this wallet: enrolment, not recovery.

    A self-transition `(counter, root) -> (counter, root)` under TAG_WM_INIT and NO_HEAD_NONCE.
    It proves the head was a genuine state, not the latest, so a WM may accept it only at
    counter 0 (enforced device-side by `adopt.verify_round_attestation`). Re-seeding a WM that
    lost its register is out of scope.
    """
    from trezor.crypto.curve import ed25519

    return ed25519.sign(
        k_sig,
        wm_preimage(
            TAG_WM_INIT, ward_id, counter, root, counter, root, NO_HEAD_NONCE
        ),
    )


def verify_head_init_sig(
    ward_id: bytes, counter: int, root: bytes | None, signature: bytes
) -> bool:
    """What the WM checks before adopting a wallet it has never seen. On the device for tests."""
    return _wm_verify(
        ward_id, signature, TAG_WM_INIT, ward_id, counter, root, counter, root, NO_HEAD_NONCE
    )
