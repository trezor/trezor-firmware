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

    ONE STEP, AND ONLY FROM WHERE THIS DEVICE STANDS. The attested predecessor must BE the
    device's stored head, so the distance this route can move the head is zero or one. It used to
    accept any counter at or above the stored one, which made the WM an authority on lineage --
    a device could be carried across dozens of transitions it never saw, on one link. See the
    rules below.

    STILL THE WEAKER OF THE TWO ROUTES, even so. One step is one step: a WM colluding with a host
    can attest a single transition off the authoritative line, and this handler will take it,
    because from the device's own head that step is indistinguishable from the real one. Only
    `verify_chain`'s walk back through every intervening link rules that out. What is gone is the
    ability to smuggle a whole HISTORY in behind one authorised step.
    """
    from trezor.messages import WardReconcileAck
    from trezor.wire import DataError

    from . import round as sync_round
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

    # HOW FAR THIS ROUTE MAY MOVE THE HEAD: nowhere, one step, or backwards with consent.
    #
    # It used to adopt ANY attested counter at or above the stored one while verifying a single
    # transition -- so a device at 10 could be moved to 40 on the strength of one link, with
    # 11..39 taken on the WM's word. That made the WM an authority on LINEAGE, which it is not
    # and must not be: an attestation establishes freshness and ordering, and DESCENT is what
    # establishes state. `verify_chain` proves descent; this route cannot, so it is now confined
    # to the distance over which there is nothing to prove.
    #
    # BATCHING IS UNAFFECTED, which is worth saying because the old comment here claimed the
    # opposite. Ten writes followed by one sync round still work -- the host publishes each
    # transition as it is made, so the WM advances one step per write and the device adopts the
    # final one from the head immediately before it. What is refused is adopting a head the
    # device never had a predecessor for, which is a gap in the history rather than a batch.
    stored_counter = await get_counter()
    stored_root = await get_root()

    if sync_round.attested_is_backward():
        # A DEMOTION, already confirmed. `recover` refuses anything that is not going backwards
        # and holds for confirmation before marking the round, so re-asking here would be asking
        # about a decision already made. The attested predecessor is historical by definition and
        # cannot be this device's head -- which is precisely why the forward rule cannot apply.
        if counter >= stored_counter:
            raise DataError("WARD: a backward round must lower the counter")

    elif counter == stored_counter:
        # NOTHING NEW. The WM names the head this device already holds, so the only question is
        # whether the two agree about what that head IS. Compared in preimage form: an empty tree
        # is stored as EMPTY_ROOT but is held as None here, and the two must still recognise
        # each other.
        if stored_root is not None and stored_root != root_or_empty(root):
            raise DataError("attested counter matches but the root differs")

    elif counter == stored_counter + 1:
        # ONE STEP, FROM WHERE THIS DEVICE STANDS. The link was verified above against the
        # attested predecessor; this is what ties that predecessor to the device's own head, and
        # without it the step could be one taken from somewhere this device has never been.
        if from_counter != stored_counter or root_or_empty(from_root) != root_or_empty(
            stored_root
        ):
            raise DataError("WARD: the attested step does not start at this device's head")

    else:
        # A GAP. Refused by name, because the alternative exists and is strictly stronger: the
        # backward walk pulls every intervening link and proves each was authorised.
        raise DataError(
            "WARD: reconcile adopts at most one step; use WardVerifyChain to catch up"
        )

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
