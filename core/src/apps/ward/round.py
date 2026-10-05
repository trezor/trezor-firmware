"""Per-session sync state, kept in the session cache: the in-flight round, the online latch,
the WM head last attested, and the user-approved demotion.

The session cache is the right lifetime for all four: none may outlive the connection that
established it, and module globals do not survive the end of a workflow.

Round layout: state(1B) || nonce(32B) || from_counter(4B BE) || from_root(32B)
                                       || to_counter(4B BE)   || to_root(32B).
"""

from micropython import const

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
    from storage.cache_common import APP_WARD_SYNC

    _set(APP_WARD_SYNC, bytes([_OPEN]) + nonce + bytes(2 * (4 + _ROOT_LEN)))


def get() -> "tuple[int, bytes, int, bytes, int, bytes] | None":
    """(state, nonce, from_counter, from_root, to_counter, to_root), or None if none is open."""
    from storage.cache_common import APP_WARD_SYNC

    from .codec import Reader

    raw = _get(APP_WARD_SYNC)
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
    from storage.cache_common import APP_WARD_SYNC

    from .codec import step_bytes

    ctx = get()
    assert ctx is not None
    _set(
        APP_WARD_SYNC,
        bytes([_ATTESTED]) + ctx[1] + step_bytes(from_counter, from_root, to_counter, to_root),
    )


def clear() -> None:
    """Close the round once adopted, so an attestation cannot be replayed into a second one."""
    from storage.cache_common import APP_WARD_SYNC

    _set(APP_WARD_SYNC, bytes(_RECORD_LEN))


# --- the online latch ---------------------------------------------------------------
#
# Set only by ADOPTING a WM-attested head (`adopt`); minting a nonce or ingesting an attestation
# proves nothing about the tree and must not set it. Session lifetime makes every new session
# start offline by construction.
_ONLINE = const(1)


def mark_online() -> None:
    """Record that this session has adopted a WM-attested head."""
    from storage.cache_common import APP_WARD_ONLINE

    _set(APP_WARD_ONLINE, bytes([_ONLINE]))


def mark_offline() -> None:
    """Drop the latch before a service build hands a mutation to the daemon.

    From that moment the outcome is unknown, so it is recorded before the request; `adopt` sets
    the latch again. Connect builds do not drop it: there only the host can re-establish a head.
    """
    from storage.cache_common import APP_WARD_ONLINE

    _set(APP_WARD_ONLINE, bytes(1))


def is_online() -> bool:
    """Whether this session has adopted a head. False (the default) routes reads offline."""
    from storage.cache_common import APP_WARD_ONLINE

    raw = _get(APP_WARD_ONLINE)
    return bool(raw) and raw[0] == _ONLINE


# --- the WM's head, as this device last saw it ----------------------------------------
#
# `(counter, root, head_nonce)`, overwritten by every verified attestation whether or not it is
# then adopted. The nonce is quoted in the next `cas.wm_sig`, so one authorisation cannot be used
# twice when a `(counter, root)` pair recurs; storing the head beside it lets
# `adopt.verify_round_attestation` check continuity against the head the nonce belongs to.
#
# Layout: flag(1B) || counter(4B BE) || root(32B, preimage form) || nonce(32B). The flag tells
# "never synced" apart from an all-zero genesis head.


def set_wm_head(counter: int, root: bytes, nonce: bytes) -> None:
    """Record the WM head an attestation just vouched for, and its freshness token."""
    from storage.cache_common import APP_WARD_WM_HEAD

    from .codec import u32

    assert len(root) == _ROOT_LEN and len(nonce) == _NONCE_LEN
    _set(APP_WARD_WM_HEAD, b"\x01" + u32(counter) + root + nonce)


def wm_head() -> "tuple[int, bytes, bytes] | None":
    """`(counter, root, head_nonce)` as this device last saw it, or None."""
    from storage.cache_common import APP_WARD_WM_HEAD

    from .codec import Reader

    raw = _get(APP_WARD_WM_HEAD)
    if not raw or len(raw) != 1 + 4 + _ROOT_LEN + _NONCE_LEN or raw[0] != 1:
        return None
    r = Reader(raw, 1)
    return r.uint(4), bytes(r.take(_ROOT_LEN)), bytes(r.take(_NONCE_LEN))


def require_head_nonce() -> bytes:
    """The head nonce, or refuse: a signature over an unknown nonce is one the WM rejects."""
    from trezor.wire import DataError

    head = wm_head()
    if head is None:
        raise DataError("WARD: no WM head nonce in this session; sync first")
    return head[2]


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


def _demotion_record(stored_counter: int, *step) -> bytes:
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
    from storage.cache_common import APP_WARD_DEMOTION

    _set(
        APP_WARD_DEMOTION,
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
    from storage.cache_common import APP_WARD_DEMOTION

    raw = _get(APP_WARD_DEMOTION)
    if not raw or raw[0] != 1:
        return False
    return raw == _demotion_record(
        stored_counter, from_counter, from_root, to_counter, to_root
    )


def clear_demotion() -> None:
    """Spend or drop the approval. A no-op when none is recorded."""
    from storage.cache_common import APP_WARD_DEMOTION

    _set(APP_WARD_DEMOTION, bytes(_DEMOTION_LEN))
