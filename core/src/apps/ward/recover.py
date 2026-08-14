from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRecoverCounter, WardRecoverCounterAck


def _age(seconds: int) -> str:
    """How far back, in terms a person can act on.

    Deliberately coarse. The decision this informs is "does that sound like the outage I
    know about, or like something else", and a precise duration would imply a precision
    the WM's clock does not have.
    """
    if seconds < 90:
        return "under a minute"
    if seconds < 3600:
        return "about %d minutes" % (seconds // 60)
    if seconds < 172800:
        return "about %d hours" % (seconds // 3600)
    return "about %d days" % (seconds // 86400)


async def recover(msg: WardRecoverCounter) -> WardRecoverCounterAck:
    """Accept an attestation that goes backwards, with the user's explicit consent.

    NAMED FOR ITS MODULE, not for what it does: `find_registered_handler` derives the
    function name from the last component of the path it is registered under, so this must
    be `recover` in `apps.ward.recover`. A mismatch fails at `getattr`, before any check in
    the body runs, so every caller sees the same opaque failure whatever it asked for.

    Monotonicity protects against replay, and when the WM's register is lost or its clock
    jumps it becomes a denial of service against the owner instead: every device with a
    stored counter locks out and nothing can sync again. This is the way back, and it is
    the ONLY path that accepts a lower counter or an older time.

    Everything here is still cryptographically genuine. The WM signature is checked
    against this round's nonce as always, and the mac must match the root supplied at
    reconcile -- and since only a device holding K_mac can produce a mac, a replayed
    (counter, mac) pair is itself proof that this wallet really did reach that state. That
    is the design's requirement that recovery target "a root the Trezor holds its own
    prior signature for", satisfied without a second mechanism.

    What cannot be checked is INTENT. Nothing distinguishes a genuine operator recovery
    from an attacker replaying old state, because both present the same authentic
    material; the difference lives entirely in whether the user means it. That makes this
    the strongest social-engineering target in the protocol, so the prompt names both
    counters, says how far back the state is, and holds -- and says plainly what is lost.
    """
    from trezor.messages import WardRecoverCounterAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import verify_attestation
    from .common import require_initialized
    from .keys import derive_ward_id
    from .root import get_counter, get_timestamp

    require_initialized()

    ctx = sync_round.get()
    if ctx is None:
        raise DataError("no sync round in progress")
    _state, nonce, _c, _m, _t = ctx

    counter = msg.counter
    mac = msg.mac
    signature = msg.wm_signature
    timestamp = msg.timestamp or 0
    if counter is None or mac is None or signature is None:
        raise DataError("counter, mac and wm_signature are required")

    if not verify_attestation(
        await derive_ward_id(), nonce, counter, mac, timestamp, signature
    ):
        raise DataError("WM attestation verification failed")

    stored_counter = await get_counter()
    stored_time = await get_timestamp()

    # Refuse to be used for anything but its purpose. An attestation that does NOT go
    # backwards belongs on the ordinary path, where it needs no confirmation -- routing it
    # through here would train users to approve this screen.
    if counter >= stored_counter and timestamp >= stored_time:
        raise DataError("attestation is not older; use the ordinary sync path")

    await confirm_properties(
        "ward_recover_counter",
        "Reset sync counter",
        [
            ("Currently at", "change #%d" % stored_counter, False),
            ("Resetting to", "change #%d" % counter, False),
            ("Going back", _age(max(stored_time - timestamp, 0)), False),
            (
                "Warning",
                "Changes after #%d may be lost. Only continue if you are recovering "
                "the sync service." % counter,
                False,
            ),
        ],
        hold=True,
    )

    sync_round.set_attested(counter, mac, timestamp)
    return WardRecoverCounterAck(counter=counter)
