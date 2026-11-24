"""Per-session sync state, kept in the session cache: the in-flight round, the online latch,
the WM head last attested, and the user-approved demotion.

The session cache is the right lifetime for all four: none may outlive the connection that
established it, and module globals do not survive the end of a workflow.

Round layout: state(1B) || nonce(32B) || from_counter(4B BE) || from_root(32B)
                                       || to_counter(4B BE)   || to_root(32B).
"""

from micropython import const

from storage import cache_common as _cc

_OPEN = const(1)  # nonce minted, nothing attested yet
_ATTESTED = const(2)  # the WM's transition has been verified for this nonce

_NONCE_LEN = const(32)
_ROOT_LEN = const(32)
# Also declared in `storage/cache_codec.py` and `storage/cache_thp.py`; a mismatch is silent.
_RECORD_LEN = const(105)
_DEMOTION_LEN = const(77)


def _get(key: int) -> "bytes | None":
    from trezor.wire import context

    return context.cache_get(key)


def _set(key: int, value: bytes) -> None:
    from trezor.wire import context

    context.cache_set(key, value)


def begin(nonce: bytes) -> None:
    """Open a round, discarding any unfinished one: only the latest nonce may be answered."""
    _set(_cc.APP_WARD_SYNC, bytes([_OPEN]) + nonce + bytes(2 * (4 + _ROOT_LEN)))


def get() -> "tuple[int, bytes, int, bytes, int, bytes] | None":
    """(state, nonce, from_counter, from_root, to_counter, to_root), or None if none is open."""
    from .codec import Reader

    raw = _get(_cc.APP_WARD_SYNC)
    if not raw or raw[0] not in (_OPEN, _ATTESTED):
        return None
    r = Reader(raw, 1)
    return (
        raw[0],
        r.take(_NONCE_LEN),
        r.uint(4),
        r.take(_ROOT_LEN),
        r.uint(4),
        r.take(_ROOT_LEN),
    )


def get_attested() -> "tuple[int, bytes, int, bytes] | None":
    """The attested transition if this round reached ATTESTED, else None."""
    ctx = get()
    if ctx is None or ctx[0] != _ATTESTED:
        return None
    return ctx[2:]


def set_attested(
    from_counter: int, from_root: bytes, to_counter: int, to_root: bytes
) -> None:
    """Record the transition the WM attested, keeping the nonce. Roots in preimage form."""
    from .codec import step_bytes

    ctx = get()
    assert ctx is not None
    _set(
        _cc.APP_WARD_SYNC,
        bytes([_ATTESTED]) + ctx[1] + step_bytes(from_counter, from_root, to_counter, to_root),
    )


def clear() -> None:
    """Close the round once adopted, so an attestation cannot be replayed into a second one."""
    _set(_cc.APP_WARD_SYNC, bytes(_RECORD_LEN))


# --- the online latch ---------------------------------------------------------------
#
# Set only by ADOPTING a WM-attested head (`adopt`); minting a nonce or ingesting an attestation
# proves nothing about the tree and must not set it. Session lifetime makes every new session
# start offline by construction.
_ONLINE = const(1)


def mark_online() -> None:
    """Record that this session has adopted a WM-attested head."""
    _set(_cc.APP_WARD_ONLINE, bytes([_ONLINE]))


def mark_offline() -> None:
    """Drop the latch before a service build hands a mutation to the daemon.

    From that moment the outcome is unknown, so it is recorded before the request; `adopt` sets
    the latch again. Connect builds do not drop it: there only the host can re-establish a head.
    """
    _set(_cc.APP_WARD_ONLINE, bytes(1))


def is_online() -> bool:
    """Whether this session has adopted a head. False (the default) routes reads offline."""
    raw = _get(_cc.APP_WARD_ONLINE)
    return bool(raw) and raw[0] == _ONLINE


# --- the provisional head: caught up without the WM -------------------------------------
#
# `WardCatchUp`'s result: a head on this wallet's own chain above the stored one that the WM once
# attested, which reads in THIS SESSION prove against. Never persisted, never "online": only a
# live WM-attested adoption moves the stored head, and `adopt` drops this.
# Layout: flag(1B) || counter(4B BE) || root(32B) || timestamp(8B BE), the timestamp the WM signed.
_PROVISIONAL_LEN = const(1 + 4 + _ROOT_LEN + 8)


def set_provisional(counter: int, root: bytes, timestamp: int) -> None:
    from .codec import u32

    assert len(root) == _ROOT_LEN
    _set(
        _cc.APP_WARD_PROVISIONAL,
        b"\x01" + u32(counter) + root + timestamp.to_bytes(8, "big"),
    )


def provisional() -> "tuple[int, bytes, int] | None":
    """`(counter, root, timestamp)` this session caught up to without the WM, or None."""
    from .codec import Reader

    raw = _get(_cc.APP_WARD_PROVISIONAL)
    if not raw or len(raw) != _PROVISIONAL_LEN or raw[0] != 1:
        return None
    r = Reader(raw, 1)
    return r.uint(4), bytes(r.take(_ROOT_LEN)), r.uint(8)


def clear_provisional() -> None:
    _set(_cc.APP_WARD_PROVISIONAL, bytes(_PROVISIONAL_LEN))


# --- the WM's head, as this device last saw it ----------------------------------------
#
# `(counter, root, session nonce, timestamp)`, overwritten by every verified attestation whether
# or not it is then adopted. The session nonce is the round nonce that attestation answered: this
# device picked it, and `cas.wm_sig` binds every authorisation to it. The WM keeps the nonce of
# the wallet's latest sync and accepts only authorisations bound to it, so a new sync by any
# device of the wallet ends the session.
#
# Layout: flag(1B) || counter(4B BE) || root(32B, preimage form) || nonce(32B)
#         || timestamp(8B BE). The flag tells "never synced" apart from an all-zero genesis head;
# the timestamp is the one the WM signed, which `adopt` persists beside the head.
_WM_HEAD_LEN = const(1 + 4 + _ROOT_LEN + _NONCE_LEN + 8)


def set_wm_head(counter: int, root: bytes, nonce: bytes, timestamp: int) -> None:
    """Record the WM head an attestation just vouched for, the session nonce it answered, and
    its time."""
    from .codec import u32

    assert len(root) == _ROOT_LEN and len(nonce) == _NONCE_LEN
    _set(
        _cc.APP_WARD_WM_HEAD,
        b"\x01" + u32(counter) + root + nonce + timestamp.to_bytes(8, "big"),
    )


def wm_head() -> "tuple[int, bytes, bytes, int] | None":
    """`(counter, root, session nonce, timestamp)` as this device last saw it, or None."""
    from .codec import Reader

    raw = _get(_cc.APP_WARD_WM_HEAD)
    if not raw or len(raw) != _WM_HEAD_LEN or raw[0] != 1:
        return None
    r = Reader(raw, 1)
    return r.uint(4), bytes(r.take(_ROOT_LEN)), bytes(r.take(_NONCE_LEN)), r.uint(8)


def require_session_nonce() -> bytes:
    """The nonce of this session's latest WM attestation, or refuse: the WM accepts an
    authorisation only when it is bound to the nonce of the wallet's latest sync."""
    from trezor.wire import DataError

    head = wm_head()
    if head is None:
        raise DataError("WARD: no WM session; sync first")
    return head[2]


# --- roll-forward: a restored WM, detected in this round -------------------------------
#
# `ingest` records that the WM attested a head below this device's stored head (DETECTED). The
# user approves re-signing the WM's accepted history on the first `WardRollForward` page
# (APPROVED). Every later page of the same round continues from where the previous ended.
#
# Layout: state(1B) || round nonce(32B) || cursor counter(4B BE) || cursor root(32B).
ROLL_FORWARD_DETECTED = const(1)
ROLL_FORWARD_APPROVED = const(2)
_ROLL_FORWARD_LEN = const(1 + _NONCE_LEN + 4 + _ROOT_LEN)


def set_roll_forward(state: int, nonce: bytes, counter: int, root: bytes) -> None:
    from .codec import u32

    assert len(nonce) == _NONCE_LEN and len(root) == _ROOT_LEN
    _set(_cc.APP_WARD_ROLL_FORWARD, bytes([state]) + nonce + u32(counter) + root)


def roll_forward() -> "tuple[int, bytes, int, bytes] | None":
    """`(state, round nonce, cursor counter, cursor root)`, or None."""
    from .codec import Reader

    raw = _get(_cc.APP_WARD_ROLL_FORWARD)
    if not raw or len(raw) != _ROLL_FORWARD_LEN or raw[0] not in (
        ROLL_FORWARD_DETECTED,
        ROLL_FORWARD_APPROVED,
    ):
        return None
    r = Reader(raw, 1)
    return raw[0], bytes(r.take(_NONCE_LEN)), r.uint(4), bytes(r.take(_ROOT_LEN))


def clear_roll_forward() -> None:
    _set(_cc.APP_WARD_ROLL_FORWARD, bytes(_ROLL_FORWARD_LEN))


# --- the authorised demotion ----------------------------------------------------------
#
# The exact transition the user held to confirm, plus the stored counter they confirmed it FROM:
# the screen's discard count is relative to that head, so consent does not survive the device
# moving on. It is the one exemption from `ingest`'s floor and `reconcile`'s one-step rule, and
# `adopt` spends it on every adoption.
#
# Layout: flag(1B) || stored_counter(4B BE) || from_counter(4B BE) || from_root(32B)
#         || to_counter(4B BE) || to_root(32B), roots in preimage form -- normalised, since
# callers pass the empty tree as None or EMPTY_ROOT and a raw comparison would never match.


def _demotion_record(stored_counter: int, *step: "int | bytes") -> bytes:
    from .codec import step_bytes, u32

    return b"\x01" + u32(stored_counter) + step_bytes(*step)


def authorise_demotion(
    stored_counter: int,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
) -> None:
    """Record the exact transition the user approved, and the head they approved it from."""
    _set(
        _cc.APP_WARD_DEMOTION,
        _demotion_record(stored_counter, from_counter, from_root, to_counter, to_root),
    )


def demotion_matches(
    stored_counter: int,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
) -> bool:
    """Is this exactly the approved demotion, from the head it was approved at?"""
    raw = _get(_cc.APP_WARD_DEMOTION)
    if not raw or raw[0] != 1:
        return False
    return raw == _demotion_record(
        stored_counter, from_counter, from_root, to_counter, to_root
    )


def clear_demotion() -> None:
    """Spend or drop the approval. A no-op when none is recorded."""
    _set(_cc.APP_WARD_DEMOTION, bytes(_DEMOTION_LEN))
