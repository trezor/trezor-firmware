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

    context.cache_set(APP_WARD_SYNC, bytes([_OPEN]) + nonce + bytes(4) + bytes(_MAC_LEN))


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
    return raw[0], nonce, counter, raw[off + 4 : off + 4 + _MAC_LEN]


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
