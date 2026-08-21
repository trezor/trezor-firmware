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
# has been checked against the freshness authority yet. Only ADOPTING a head changes that,
# because only then has a WM attestation been bound to an actual tree.
#
# So this is a LATCH SET BY ADOPTION ALONE, which is `reconcile` and `verify_chain` and nothing
# else. `WardSync` mints a nonce and proves nothing; `WardIngestAttestation` verifies a signature
# over a counter and a mac but adopts neither. Neither may flip it.
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

    No connect-mode route needs this: nothing there moves the backend's head without the device
    having adopted the result in the same breath.

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
