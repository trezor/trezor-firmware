"""The in-flight sync round: the nonce, and what the WM attested against it.

A round spans THREE separate requests -- mint the nonce, ingest the attestation, adopt
the root -- so its state cannot live in a module global: `trezor.wire` discards every
module a workflow imported once that workflow ends. It lives in the session cache, which
is also the right lifetime: an unfinished round should not outlive the connection that
started it.

Layout: state(1B) || nonce(32B) || from_counter(4B BE) || from_root(32B)
                                 || to_counter(4B BE)   || to_root(32B).

BOTH ENDS, because the WM attests a TRANSITION -- see `attest.attestation_preimage`. The `from`
pair is what `reconcile` recomputes the link's `auth_commit` over, so it has to survive the host
turn between `WardIngestAttestation` and the adoption that consumes it.
"""

from micropython import const

_OPEN = const(1)  # nonce minted, nothing attested yet
_ATTESTED = const(2)  # the WM's transition has been verified for this nonce

_NONCE_LEN = const(32)
_ROOT_LEN = const(32)
# state + nonce + (counter, root) twice. DUPLICATED in the cache field tables --
# `storage/cache_codec.py` and `storage/cache_thp.py` both declare this width, and a mismatch
# there is silent: the store's length check is `<=`, so a short write simply reads back as an
# unopened round.
_RECORD_LEN = const(105)


def begin(nonce: bytes) -> None:
    """Open a round. Any previous unfinished round is discarded, which is deliberate:
    only the most recent nonce may be answered, so a host cannot keep several rounds in
    flight and choose which one an attestation applies to."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    context.cache_set(
        APP_WARD_SYNC,
        bytes([_OPEN]) + nonce + (bytes(4) + bytes(_ROOT_LEN)) * 2,
    )


def get() -> "tuple[int, bytes, int, bytes, int, bytes] | None":
    """(state, nonce, from_counter, from_root, to_counter, to_root), or None if none is open."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_SYNC)
    if not raw or raw[0] not in (_OPEN, _ATTESTED):
        return None
    nonce = raw[1 : 1 + _NONCE_LEN]
    off = 1 + _NONCE_LEN
    from_counter = int.from_bytes(raw[off : off + 4], "big")
    from_root = raw[off + 4 : off + 4 + _ROOT_LEN]
    off += 4 + _ROOT_LEN
    to_counter = int.from_bytes(raw[off : off + 4], "big")
    to_root = raw[off + 4 : off + 4 + _ROOT_LEN]
    return raw[0], nonce, from_counter, from_root, to_counter, to_root


def get_attested() -> "tuple[int, bytes, int, bytes] | None":
    """The attested transition if this round reached ATTESTED, else None.

    The state constants are `const()`-folded and therefore absent from the module at runtime, so
    the ATTESTED test has to live here rather than in the caller.
    """
    ctx = get()
    if ctx is None or ctx[0] != _ATTESTED:
        return None
    _state, _nonce, from_counter, from_root, to_counter, to_root = ctx
    return from_counter, from_root, to_counter, to_root


def set_attested(
    from_counter: int, from_root: bytes, to_counter: int, to_root: bytes
) -> None:
    """Record the transition the WM attested, keeping the round's nonce.

    Both roots arrive in PREIMAGE FORM -- an empty tree as EMPTY_ROOT -- because that is what the
    signature covered and what a later recomputation has to reproduce.

    """
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    ctx = get()
    assert ctx is not None
    _state, nonce, _fc, _fr, _tc, _tr = ctx
    context.cache_set(
        APP_WARD_SYNC,
        bytes([_ATTESTED])
        + nonce
        + from_counter.to_bytes(4, "big")
        + from_root
        + to_counter.to_bytes(4, "big")
        + to_root,
    )


def clear() -> None:
    """Close the round. Called once its result is adopted, so an attestation can never be
    replayed into a second adoption."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    context.cache_set(APP_WARD_SYNC, bytes(_RECORD_LEN))


# --- the online latch -------------------------------------------------------------
#
# WHAT "ONLINE" MEANS, and why it is a device-side fact rather than something the host tells us.
# A session begins knowing nothing current: the stored root may be any age, and no host claim
# has been checked against the freshness authority yet. Only ADOPTING a head changes that,
# because only then has a WM attestation been bound to an actual tree.
#
# So this is a LATCH SET BY ADOPTION ALONE, which is `reconcile` and `verify_chain` and nothing
# else. `WardSync` mints a nonce and proves nothing; `WardIngestAttestation` verifies a signature
# over a transition but adopts neither end of it. Neither may flip it.
#
# `verify_chain` latches for the same reason `reconcile` does, and it is the stricter of the two:
# it additionally proves authorised descent from the head this device already held. Leaving it
# out meant the stronger route was the one a device could not come online by -- which is the
# route multi-device catch-up arrives on.
#
# It lives in the session cache for its LIFETIME, not its size: a new session and a power cycle
# both have to start offline, and putting it here means that happens by construction rather
# than by remembering to clear it somewhere. Flash would have needed a reset path, and a missed
# reset would leave a device claiming currency it has not established -- "cannot verify" reading
# as "verified" again, which is the failure direction this subsystem keeps having to close.
#
# A host that never syncs therefore leaves the device offline forever, and that is CORRECT
# rather than a degradation to work around: a host that does not speak WARD cannot answer
# `WardEntryRequest` either, so reads are served from the offline store and say so on screen.
_ONLINE = const(1)


def mark_online() -> None:
    """Record that this session has adopted a WM-attested head.

    Called by the two handlers that ADOPT one -- `reconcile` and `verify_chain` -- and by
    nothing else. `WardSync` mints a nonce and proves nothing; `WardIngestAttestation`
    verifies a signature but adopts no tree. Neither may flip it.
    """
    from storage.cache_common import APP_WARD_ONLINE
    from trezor.wire import context

    context.cache_set(APP_WARD_ONLINE, bytes([_ONLINE]))


def mark_offline() -> None:
    """Drop the latch: this session no longer knows it shares a head with the backend.

    THE ONLY THING THAT CLEARS IT, and it exists for one moment: a service build about to hand a
    mutation to the daemon. From the instant that request leaves, the device cannot say whether the
    daemon applied it -- an ack that never arrives is indistinguishable from a write that never
    happened -- so the honest state is "I do not know", and it has to be recorded BEFORE the
    request rather than after the failure. Clearing it afterwards would leave the whole window in
    which the answer is unknown looking like the window in which it is known.

    CONNECT MODE HAS THE SAME WINDOW AND DOES NOT DROP THE LATCH, which is a decision rather than
    an oversight -- the reason this used to give ("nothing there moves the backend's head without
    the device having adopted the result in the same breath") is simply wrong. `set_entry` /
    `delete_entry` / `flush_queue` hand the host a candidate and return without persisting it, so
    from that moment the host may move the backend's head while this session still believes its
    older root is current.

    WHAT STOPS IT BEING THE SAME FIX. A service build closes its own window: it publishes and
    adopts the answer, so the gap is one round trip and the device ends it. A connect build cannot
    -- only the host can re-establish a head here -- so dropping the latch does not narrow a window,
    it ends the session's ability to act until the host reconciles. Measured: it fails the queue
    drain loop (`remaining > 0` issues a second mutation), the lost-response delete retry, and a
    read after a write. Seven device tests, all of them legitimate flows.

    So the honest statement is that a connect session can hold a superseded head, that the screens
    already say a value is not proven current, and that the fix is per-use freshness rather than a
    latch -- a WM attestation taken immediately before a decision that needs one. A latch cannot
    express "still current"; it only ever meant "this session reconciled once".

    NOT A FAILURE PATH. `adopt` sets the latch again as the last thing it does, so the ordinary
    outcome is a gap of one round trip.
    """
    from storage.cache_common import APP_WARD_ONLINE
    from trezor.wire import context

    context.cache_set(APP_WARD_ONLINE, bytes(1))


def is_online() -> bool:
    """Whether a reconcile has succeeded in THIS session.

    False is the safe answer and the default: it routes reads to the offline store, where the
    screens say what they can and cannot vouch for. It never causes a stale value to be
    presented as current.
    """
    from storage.cache_common import APP_WARD_ONLINE
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_ONLINE)
    return bool(raw) and raw[0] == _ONLINE


# --- the WM's head, as this device last saw it ------------------------------------------
#
# `(counter, root, head_nonce)` -- the WM's whole state, latched when an attestation for it
# verifies. The nonce is the freshness token the WM rotates on every transition it accepts; the
# device learns it from inside the signed attestation and quotes it forward in the next
# `cas.wm_sig`, which is what stops one authorisation being usable twice when a `(counter, root)`
# pair recurs.
#
# THE HEAD IS STORED BESIDE THE NONCE, not just the nonce, and that pairing is what makes the
# continuity rules in `adopt.verify_round_attestation` safe. A bare nonce would have to be
# compared against the device's FLASH head, and the two can legitimately disagree -- an
# attestation may verify and then fail to be adopted, leaving a nonce for a head the device does
# not hold. Comparing an attested end against the head the nonce actually belongs to removes that
# whole class of false refusal.
#
# WHY IT IS NOT IN THE ROUND RECORD. A write happens in a LATER request than the round that
# brought the nonce in: `adopt` calls `clear()` as its last act, so a value kept on the round is
# gone by the time anything needs it. It lives beside the online latch instead, and for the same
# lifetime -- which is also the right rule, because `online()` is exactly the condition under
# which a nonce has been established this session. A new session must sync before it may write,
# and must therefore learn a current nonce before it may authorise one.
#
# SESSION LIFETIME IS ALSO ITS LIMIT, stated plainly: the continuity rules can only catch a WM
# register that moved incoherently WITHIN a session. Across a power cycle the device starts with
# no nonce and the first attestation of the new session is unchecked. Persisting it beside the
# root in `storage.ward` would extend the check across sessions, at 32 bytes per wallet slot.
#
# ALWAYS THE FRESHEST ONE SEEN. Every successful `adopt.verify_round_attestation` overwrites it,
# whether or not the adoption that follows succeeds -- a nonce is a WM fact, not an outcome of
# ours, and holding an older one buys nothing: presenting a stale nonce yields a signature the WM
# refuses, which is a failed write and not a forged one.
#
# Layout: flag(1B) || counter(4B BE) || root(32B) || nonce(32B). The root is in PREIMAGE form,
# the form an attestation carries, so comparison is plain equality.


def set_wm_head(counter: int, root: bytes, nonce: bytes) -> None:
    """Record the WM head an attestation just vouched for, and its freshness token."""
    from storage.cache_common import APP_WARD_WM_HEAD
    from trezor.wire import context

    assert len(root) == _ROOT_LEN and len(nonce) == _NONCE_LEN
    # A PRESENCE BYTE. An unset cache slot reads back as zeros, which would otherwise parse as a
    # perfectly well-formed head -- counter 0, an all-zero root, an all-zero nonce -- and "we
    # have never synced" would be indistinguishable from "the WM is at genesis". The flag is
    # cheaper than reasoning about whether any of those three could occur together.
    context.cache_set(
        APP_WARD_WM_HEAD,
        b"\x01" + counter.to_bytes(4, "big") + root + nonce,
    )


def wm_head() -> "tuple[int, bytes, bytes] | None":
    """`(counter, root, head_nonce)` as this device last saw it, or None.

    None is the safe answer: a caller that cannot name the WM's head cannot check continuity
    against it and cannot mint an authorisation the WM would accept.
    """
    from storage.cache_common import APP_WARD_WM_HEAD
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_WM_HEAD)
    if not raw or len(raw) != 1 + 4 + _ROOT_LEN + _NONCE_LEN or raw[0] != 1:
        return None
    return (
        int.from_bytes(raw[1:5], "big"),
        bytes(raw[5 : 5 + _ROOT_LEN]),
        bytes(raw[5 + _ROOT_LEN :]),
    )


def head_nonce() -> "bytes | None":
    """Just the freshness token, for the callers that only mint against it."""
    head = wm_head()
    return head[2] if head is not None else None


def require_head_nonce() -> bytes:
    """The head nonce, or refuse to authorise anything.

    Signing against an unknown nonce would produce an authorisation the WM cannot accept, and the
    failure would surface at the host as a rejected publish with no explanation. Fail here, where
    the reason is nameable.
    """
    from trezor.wire import DataError

    nonce = head_nonce()
    if nonce is None:
        raise DataError("WARD: no WM head nonce in this session; sync first")
    return nonce


# --- the authorised demotion ---------------------------------------------------------
#
# The exact TRANSITION the user approved the head coming down to, recorded when they confirm and
# spent when it is adopted.
#
# THE WHOLE STEP, NOT JUST THE COUNTER. A counter alone would admit any genuine attestation
# landing on that number -- including one for a different root, which is a different demotion
# than the one the user was shown. The device minted the transition itself, so it knows all four
# operands and can require the attestation that comes back to be exactly it. Consent is for a
# specific state, and this is what makes the code say so.
#
# WHY IT CANNOT LIVE IN THE ROUND. A demotion is minted against the WM's head and then has to be
# PUBLISHED before any device may adopt it -- the head only moves when the WM confirms, which is
# the invariant every other write obeys too. That publication is a round trip, and the sync round
# that brings the new attestation back is a DIFFERENT round: `begin` discards the old one, so a
# flag on it is gone exactly when it is needed. It lives beside the online latch instead, for the
# same lifetime and the same reason -- a demotion not completed in this session must be confirmed
# again rather than inherited.
#
# WHAT IT IS FOR. `ingest` refuses any counter below the stored floor, and `reconcile` refuses any
# head that is not one step from where the device stands. Both are right, and both would refuse a
# demotion -- the whole point of which is to come down. This is the one value that lets them.
#
# Layout: flag(1B) || from_counter(4B BE) || from_root(32B) || to_counter(4B BE) || to_root(32B).
# Roots are kept in PREIMAGE form, the form an attestation carries, so the comparison is a plain
# equality rather than a normalisation each caller could get wrong.


def authorise_demotion(
    from_counter: int, from_root: bytes, to_counter: int, to_root: bytes
) -> None:
    """Record the exact transition the user approved."""
    from storage.cache_common import APP_WARD_DEMOTION
    from trezor.wire import context

    context.cache_set(
        APP_WARD_DEMOTION,
        b"\x01"
        + from_counter.to_bytes(4, "big")
        + from_root
        + to_counter.to_bytes(4, "big")
        + to_root,
    )


def authorised_demotion() -> "tuple[int, bytes, int, bytes] | None":
    """The transition a demotion was approved for, or None. Absent is the safe answer."""
    from storage.cache_common import APP_WARD_DEMOTION
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_DEMOTION)
    if not raw or raw[0] != 1:
        return None
    return (
        int.from_bytes(raw[1:5], "big"),
        raw[5:37],
        int.from_bytes(raw[37:41], "big"),
        raw[41:73],
    )


def clear_demotion() -> None:
    """Spend it. Called once the demotion is adopted, so one confirmation buys one descent."""
    from storage.cache_common import APP_WARD_DEMOTION
    from trezor.wire import context

    context.cache_set(APP_WARD_DEMOTION, bytes(73))
