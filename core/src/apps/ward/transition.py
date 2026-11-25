"""Transitions: authorising a transition from one root to the next. The ONLY authority on state.

    preimage   = len8(tag) || tag || ward_id || from_counter(4B BE) || from_root(32B)
                                             || to_counter(4B BE)   || to_root(32B)
    AuthCommit = HMAC-SHA256(K_auth, preimage)

`tag` is TAG_COMMIT for a write and TAG_REVERT for a rollback; an empty tree is EMPTY_ROOT.

A MAC, because exactly the seed holders need to verify it; the WM gets its own authenticator over
the same bytes plus the session nonce (`wm_sig`). The WM could attest a root the wallet never held;
descent through K_auth links (`verify_chain`) catches that. A chain proves descent, not currency --
the WM attestation supplies that.
"""

from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardChainLink

# The most changes one transition (a batch) may carry; every step rule is
# "1 <= to - from <= MAX_BATCH". Variable steps mean every walk must land EXACTLY.
MAX_BATCH = const(8)

TAG_COMMIT = b"WARD COMMIT v3"
TAG_REVERT = b"WARD REVERT v3"

# The WM's own authorisations: `transition_preimage` plus the session nonce (`wm_sig`). Enrolment
# happens before any session, so TAG_WM_INIT carries none.
TAG_WM_HEAD = b"WARD WM COMMIT v5"
TAG_WM_INIT = b"WARD WM INIT v4"
# Lets a WM apply policy to demotions; the predecessor check is what stops a replay.
TAG_WM_REVERT = b"WARD WM REVERT v5"
# Without a WM (the MVP build): the same step signed for the HOST, so a host can refuse to store
# a write no device of this wallet made. Its own tag, so it is never a WM authorisation.
TAG_STEP = b"WARD STEP v2"


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
    operand the WM acts on is inside the bytes it verifies.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty
    from .codec import step_bytes

    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if len(ward_id) != 32 or len(from_root) != 32 or len(to_root) != 32:
        raise DataError("WARD: transition operands must be 32 bytes")

    # Length-prefixed tag: tags differ in length, so no cross-domain collision.
    return (
        bytes([len(tag)])
        + tag
        + ward_id
        + step_bytes(from_counter, from_root, to_counter, to_root)
    )


def _mac(key: bytes, preimage: bytes) -> bytes:
    from trezor.crypto import hmac

    return hmac(hmac.SHA256, key, preimage).digest()


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
    return _mac(
        k_auth,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root),
    )


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

    # CONSTANT TIME: `mac` comes from the host, and bytes `==` short-circuits.
    return consteq(
        auth_commit(k_auth, ward_id, from_counter, from_root, to_counter, to_root, tag),
        mac,
    )


def link_of(msg: "WardChainLink") -> tuple:
    """A wire link as `(from_counter, from_root, to_counter, to_root, auth_commit)`."""
    return (
        msg.from_counter,
        msg.from_root or None,
        msg.to_counter,
        msg.to_root or None,
        msg.auth_commit,
    )


def link_kind(
    k_auth: bytes, ward_id: bytes, link: tuple, error: str = "WARD: chain link is not authorised"
) -> bool:
    """Is this link a REVERT (True) or a COMMIT (False)? DataError(error) if it is neither.

    Both kinds are real transitions for descent; which one it was is reported, not swallowed.
    """
    from trezor.wire import DataError

    for tag, is_revert in ((TAG_COMMIT, False), (TAG_REVERT, True)):
        if verify_auth_commit(k_auth, ward_id, *link, tag):
            return is_revert
    raise DataError(error)


def verify_chain_step(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: bytes | None,
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
    """Fold one link (from_counter, from_root, to_counter, to_root, auth_commit) FORWARD: its `from`
    must be the running head and it must advance by 1..MAX_BATCH, both checked before the MAC."""
    from trezor.wire import DataError

    from .attest import same_root

    fc, fr, tc, tr, _mac = link
    if fc != running_counter:
        raise DataError("WARD: chain link does not follow the running counter")
    if not same_root(fr, running_root):
        raise DataError("WARD: chain link does not follow the running root")
    if not 1 <= tc - running_counter <= MAX_BATCH:
        raise DataError("WARD: chain link must advance the counter by 1 to MAX_BATCH")
    return tc, tr, link_kind(k_auth, ward_id, link)


def verify_chain_step_back(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: "bytes | None",
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
    """Fold one link BACKWARD off the running head; returns its predecessor and `is_revert`.

    Not a flag on the forward fold: which end is pinned is the whole security of a walk. The `to`
    end is pinned by an established state, so an orphaned link is refused before its MAC is
    computed. The calling walk must land EXACTLY on its stop counter.
    """
    from trezor.wire import DataError

    from .attest import same_root

    fc, fr, tc, tr, _mac = link
    if tc != running_counter:
        raise DataError("WARD: chain link does not end at the running counter")
    if not same_root(tr, running_root):
        raise DataError("WARD: chain link does not end at the running root")
    if not 1 <= running_counter - fc <= MAX_BATCH:
        raise DataError("WARD: chain link must step the counter back by 1 to MAX_BATCH")
    return fc, fr, link_kind(k_auth, ward_id, link)


# --- the queued INTENT: a MAC under K_auth so a backed-up queued change can be recognised when it
# comes back. It binds the identity (a queued change has no path yet), not a counter.

TAG_RETRY = b"WARD RETRY v1"


def retry_preimage(
    ward_id: bytes,
    base: int,
    seen: int,
    entry_key: bytes,
    entry_type: str,
    value: "bytes | None",
) -> bytes:
    """The bytes a write's retry token covers: the write itself and where it was formed.

    `base` is the counter it was formed on and `seen` the C_leaf of the entry there (0: absent).
    `value` None is a delete, which has no type. Length-prefixed where a field is variable.
    """
    from trezor.wire import DataError

    from .codec import lp, u32

    if len(ward_id) != 32 or len(entry_key) != 32:
        raise DataError("WARD: retry operands must be 32 bytes")
    body = TAG_RETRY + ward_id + u32(base) + u32(seen) + entry_key
    if value is None:
        return body + b"\x00"
    return body + b"\x01" + lp(1, entry_type.encode(), "WARD: entry_type too long") + value


def retry_mac(k_auth: bytes, *operands) -> bytes:
    """Authenticate a write so that, if it loses a race, the host can present it again."""
    return _mac(k_auth, retry_preimage(*operands))


def verify_retry_mac(k_auth: bytes, mac: bytes, *operands) -> bool:
    """Did a device of this wallet form EXACTLY this write, on this base?"""
    from trezor.utils import consteq

    return consteq(retry_mac(k_auth, *operands), mac)


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

    from .codec import lp

    if len(ward_id) != 32:
        raise DataError("WARD: intent operands must be 32 bytes")
    names = "WARD: key_type or app_id too long to authenticate"
    sizes = "WARD: identifier or value too long to authenticate"
    return (
        TAG_INTENT
        + ward_id
        + bytes([op])
        + lp(1, key_type.encode(), names)
        + lp(1, app_id.encode(), names)
        + lp(2, identifier, sizes)
        + lp(2, value, sizes)
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
    return _mac(k_auth, intent_preimage(ward_id, op, key_type, app_id, identifier, value))


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

    return consteq(
        intent_mac(k_auth, ward_id, op, key_type, app_id, identifier, value), mac
    )


# --- the WM's authorisation: Ed25519 under K_sig (`ward_id` is its public key) over
# `transition_preimage` || session nonce. The session nonce is the round nonce this device picked
# for its latest sync, which the WM's attestation answered (`round.wm_head`); the WM never picks
# one. The WM keeps the nonce of the wallet's latest sync, replaces it on the next sync, and
# accepts an authorisation only when it is bound to that nonce and its predecessor is the WM's
# head (predecessor check). One session may carry several transitions; every accepted one raises
# the counter, so an authorisation moves the head at most once.
#
# A NEW SYNC ENDS THE SESSION, and with it every authorisation minted in it that has not landed:
# a lost race, or a write a host held back. The session nonce is volatile and must not come back
# with a restored backup, so a restored WM does not take them either. What the WM accepted before
# a restore comes back by ROLL-FORWARD: a host presents the WM's OWN signed record of each
# transition, which the WM verifies with its own key. See docs/ward/ward_transitions.md and
# docs/ward/ward_manager.md.


def wm_sig(
    k_sig: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    tag: bytes = TAG_WM_HEAD,
    session_nonce: bytes = b"",
) -> bytes:
    """Authorise a head advance to the WM (TAG_WM_HEAD, or TAG_WM_REVERT for a demotion), bound to
    `session_nonce`. Enrolment (TAG_WM_INIT) and the MVP's host step (TAG_STEP) carry none."""
    from trezor.crypto.curve import ed25519

    if session_nonce and len(session_nonce) != 32:
        raise ValueError
    return ed25519.sign(
        k_sig,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root)
        + session_nonce,
    )


async def authorise(
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    revert: bool = False,
) -> "tuple[bytes, bytes]":
    """`(auth_commit, wm_sig)` for one transition: the device-facing MAC and the WM-facing
    signature over the same step, the latter bound to this session's nonce. Every minting path
    goes through here, so the two can never name different transitions.

    A firmware built without a WM (the MVP) has no WM to present it to, so the second element is
    the step signed for the HOST instead: under TAG_STEP, verifiable with `ward_id` alone. It lets
    a host refuse a write no device of this wallet made. A revert cannot be minted there (it needs
    an attested round)."""
    from trezor import utils

    from . import round as sync_round
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id

    ward_id = await derive_ward_id()
    ops = (ward_id, from_counter, from_root, to_counter, to_root)
    step = auth_commit(await derive_k_auth(), *ops, TAG_REVERT if revert else TAG_COMMIT)
    if not utils.USE_WARD_WM:
        return step, wm_sig(await derive_k_sig(), *ops, TAG_STEP)
    return (
        step,
        wm_sig(
            await derive_k_sig(),
            *ops,
            TAG_WM_REVERT if revert else TAG_WM_HEAD,
            sync_round.require_session_nonce(),
        ),
    )


def session_proof(
    k_sig: bytes, ward_id: bytes, challenge: bytes, nonce: bytes
) -> bytes:
    from trezor.crypto.curve import ed25519
    from trezor.wire import DataError

    if len(challenge) != 32 or len(nonce) != 32:
        raise DataError("WARD: invalid session challenge or nonce")
    return ed25519.sign(k_sig, b"WARD SESSION OPEN v1" + ward_id + challenge + nonce)


def head_init_sig(
    k_sig: bytes, ward_id: bytes, counter: int, root: bytes | None
) -> bytes:
    """Authorise the FIRST head a WM holds for this wallet: a self-transition under TAG_WM_INIT.
    It proves a genuine state, not the latest, so it is valid only at counter 0. It is not
    secret: a WM whose register was wiped can be enrolled again with it."""
    return wm_sig(k_sig, ward_id, counter, root, counter, root, TAG_WM_INIT)
