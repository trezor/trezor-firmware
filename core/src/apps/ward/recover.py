from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRecoverCounter, WardRecoverCounterAck


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

    Everything here is still cryptographically genuine: the WM signature is checked against this
    round's nonce as always. What it is NO LONGER proof of is that the wallet ever reached the
    state it names. That used to follow for free -- the attested value was a mac only a
    seed-holding device could produce, so a replay was self-evidently of real history -- and with
    the WM attesting roots in the clear, it does not. The proof has moved to where every other
    proof of state now lives: the adoption that follows must fold an authorised LINK into the
    recovered head (`reconcile`) or walk the chain to it (`verify_chain`), and a host that cannot
    produce one cannot complete a recovery. Fail-closed, and it is the same requirement the design
    stated as targeting "a root the Trezor holds its own prior signature for".

    What cannot be checked is INTENT. Nothing distinguishes a genuine operator recovery
    from an attacker replaying old state, because both present the same authentic
    material; the difference lives entirely in whether the user means it. That makes this
    the strongest social-engineering target in the protocol, so the prompt names both
    counters, says how far back the state is, and holds -- and says plainly what is lost.

    "How far back" is a COUNT, not a duration. The device has no clock, and the stored time it
    once compared against is gone with the rest of the timestamp: it was never a security
    signal, since a malicious WM lies about the clock freely. The count is authenticated --
    both counters come from verified material -- which the duration never was.
    """
    from trezor.messages import WardRecoverCounterAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_round_attestation
    from .common import require_initialized
    from .root import get_counter

    require_initialized()

    from_counter, from_root, counter, root = await verify_round_attestation(
        msg.from_counter,
        msg.from_root or None,
        msg.to_counter,
        msg.to_root or None,
        msg.timestamp or 0,
        msg.wm_signature,
    )

    stored_counter = await get_counter()

    # Refuse to be used for anything but its purpose. An attestation that does NOT go
    # backwards belongs on the ordinary path, where it needs no confirmation -- routing it
    # through here would train users to approve this screen.
    if counter >= stored_counter:
        raise DataError("attestation is not older; use the ordinary sync path")

    await confirm_properties(
        "ward_recover_counter",
        "Reset sync counter",
        [
            ("Currently at", "change #%d" % stored_counter, False),
            ("Resetting to", "change #%d" % counter, False),
            ("Going back", "%d changes" % (stored_counter - counter), False),
            (
                "Warning",
                "Changes after #%d may be lost. Only continue if you are recovering "
                "the sync service." % counter,
                False,
            ),
        ],
        hold=True,
    )

    sync_round.set_attested(from_counter, from_root, counter, root)
    return WardRecoverCounterAck(counter=counter)
