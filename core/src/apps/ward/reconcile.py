from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardReconcile, WardReconcileAck


async def reconcile(msg: WardReconcile) -> WardReconcileAck:
    """Adopt the attested head, having folded the single link that produced it.

    THE HOST NAMES NOTHING BUT 32 BYTES. The WM attests the whole step -- both counters and both
    roots -- so all four operands arrive inside the signature this round already verified. What
    the host contributes is the `auth_commit` over that same step, and only a holder of this
    wallet's K_auth can mint one. Two signatures, two secrets, one statement.

    WHY THE LINK IS NEEDED AT ALL. The WM signs roots in the clear, so its signature says a
    trusted authority calls this step current and says nothing about whether the wallet ever took
    it: a WM that invented a transition would be believed on its own word. The MAC is what makes
    it a statement about this wallet.

    STILL THE WEAKER OF THE TWO ROUTES. Not because the host can substitute anything -- it cannot
    any more -- but because one step is all this proves. It does not show that the attested
    predecessor descends from THIS device's head, so a WM colluding with a host can attest a step
    off the authoritative line and this handler will take it. `verify_chain` walks back to a state
    the device already holds and rules that out by construction. Prefer it; this exists for the
    one-step case.
    """
    from trezor.messages import WardReconcileAck
    from trezor.wire import DataError

    from .adopt import adopt, require_attested_round, verify_inbound_link
    from .attest import root_or_empty
    from .common import require_initialized
    from .root import get_counter, get_root

    require_initialized()

    from_counter, from_root, counter, root = require_attested_round("reconcile")

    # THE LINK IS CHECKED IN PREIMAGE FORM, before the empty tree is normalised away: that is
    # what the signature covered and what `auth_commit` has to be recomputed over.
    reverted = await verify_inbound_link(
        from_counter, from_root, counter, root, msg.auth_commit
    )

    # The empty tree travels as EMPTY_ROOT inside the preimage and is held as None everywhere
    # above here. Normalise once, now that nothing else needs the signed form.
    from .attest import EMPTY_ROOT

    if root == EMPTY_ROOT:
        root = None

    # One counter names one state. If the WM attests the counter this device already
    # holds, the state it names must be the state this device already has -- otherwise one
    # of the two is wrong and adopting either silently discards the other.
    #
    # A strictly greater counter is adopted, and that is now safe: writes advance the
    # counter too, so a device with unpublished writes is AHEAD of the WM and its
    # attestation is refused by the floor check rather than superseding them. The device
    # is then unable to sync until the host publishes the (counter, root) it was handed --
    # fail-closed and recoverable, rather than a silent loss.
    #
    # A LOWER counter is adopted here without further ceremony, and that is not a hole: the
    # only way one reaches an attested round is through WardRecoverCounter, which refuses
    # anything that is not going backwards and holds for confirmation first. Re-asking here
    # would be asking about a decision already made.
    # This is also what makes BATCHING WM confirmations free today, which is worth stating
    # because it looks like missing work: a write commits its root with no WM involvement at
    # all, and any counter above the stored one is adopted here, so ten writes followed by one
    # sync round is already the supported shape. Batching only becomes real work if writes ever
    # commit solely on WM confirmation -- then each needs its own round, and amortising them is
    # part of that change rather than a prerequisite for it. See `storage/ward.py`.
    stored_counter = await get_counter()
    if counter == stored_counter:
        current = await get_root()
        # Compared in preimage form: an empty tree is stored as EMPTY_ROOT but is held as None
        # here, and the two must still recognise each other.
        if current is not None and current != root_or_empty(root):
            raise DataError("attested counter matches but the root differs")

    # Everything after this point is shared with `verify_chain` -- settle, persist, latch, close
    # -- and the order within it is load-bearing. See `adopt`.
    #
    # THE LINK IS THE EVIDENCE, not the counter. A claim filed by `flush_queue` carries the
    # `auth_commit` of its own transition, so handing this one over settles exactly the change
    # that landed rather than every change the counter happened to move past.
    await adopt(counter, root, landed_commits=[msg.auth_commit] if msg.auth_commit else None)

    if reverted:
        from .verify_chain import warn_reached_by_revert

        await warn_reached_by_revert(1)

    return WardReconcileAck(counter=counter, new_root=root)
