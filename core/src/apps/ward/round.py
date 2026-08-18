"""The in-flight sync round: the nonce, and what the WM attested against it.

A round spans THREE separate requests -- mint the nonce, ingest the attestation, adopt
the root -- so its state cannot live in a module global: `trezor.wire` discards every
module a workflow imported once that workflow ends. It lives in the session cache, which
is also the right lifetime: an unfinished round should not outlive the connection that
started it.

Layout: state(1B) || nonce(32B) || counter(4B BE) || mac(32B).
"""

from micropython import const

_OPEN = const(1)  # nonce minted, nothing attested yet
_ATTESTED = const(2)  # the WM's (counter, mac) has been verified for this nonce

_NONCE_LEN = const(32)
_MAC_LEN = const(32)


def begin(nonce: bytes) -> None:
    """Open a round. Any previous unfinished round is discarded, which is deliberate:
    only the most recent nonce may be answered, so a host cannot keep several rounds in
    flight and choose which one an attestation applies to."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    context.cache_set(
        APP_WARD_SYNC, bytes([_OPEN]) + nonce + bytes(4) + bytes(_MAC_LEN)
    )


def get() -> "tuple[int, bytes, int, bytes] | None":
    """(state, nonce, counter, mac), or None if no round is open."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_SYNC)
    if not raw or raw[0] not in (_OPEN, _ATTESTED):
        return None
    nonce = raw[1 : 1 + _NONCE_LEN]
    off = 1 + _NONCE_LEN
    counter = int.from_bytes(raw[off : off + 4], "big")
    mac = raw[off + 4 : off + 4 + _MAC_LEN]
    return raw[0], nonce, counter, mac


def set_attested(counter: int, mac: bytes) -> None:
    """Record what the WM attested, keeping the round's nonce."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    ctx = get()
    assert ctx is not None
    _state, nonce, _c, _m = ctx
    context.cache_set(
        APP_WARD_SYNC,
        bytes([_ATTESTED]) + nonce + counter.to_bytes(4, "big") + mac,
    )


def clear() -> None:
    """Close the round. Called once its result is adopted, so an attestation can never be
    replayed into a second adoption."""
    from storage.cache_common import APP_WARD_SYNC
    from trezor.wire import context

    context.cache_set(APP_WARD_SYNC, bytes(69))


# --- the online latch -------------------------------------------------------------
#
# WHAT "ONLINE" MEANS, and why it is a device-side fact rather than something the host tells us.
# A session begins knowing nothing current: the stored root may be any age, and no host claim
# has been checked against the freshness authority yet. Only a completed reconcile changes
# that, because only there has a WM attestation been bound to an actual tree.
#
# So this is a LATCH SET BY RECONCILE ALONE. `WardSync` mints a nonce and proves nothing;
# `WardIngestAttestation` verifies a signature over a counter and a mac but adopts neither.
# Neither may flip it.
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
    """Record that this session has adopted a WM-attested head. Called only by `reconcile`."""
    from storage.cache_common import APP_WARD_ONLINE
    from trezor.wire import context

    context.cache_set(APP_WARD_ONLINE, bytes([_ONLINE]))


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
