from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRejoin, WardRejoinAck


async def rejoin(msg: WardRejoin) -> WardRejoinAck:
    """Rejoin the WM's history after it lost the branch this device stands on.

    HOW A DEVICE GETS HERE. It only ever adopts WM-attested heads, so a head it holds was once
    the WM's. If the WM's register is then restored below that head -- a backup, a failover onto
    a stale replica -- other devices write on from the restored point and the WM's history no
    longer contains this device's head. `verify_chain` walks back to this device's counter,
    arrives at a different root and refuses, correctly: it must never adopt a history that does
    not continue the one it holds. `reconcile` refuses the gap, and `rollback` builds a step from
    the WM's head that fails the same descent. Without this the device could never sync again.

    WHAT IS PROVED, and it is the whole of the safety argument. Both branches are walked back to
    `fork_counter` under K_auth, pulled exactly as `verify_chain` pulls them:

      the WM's branch   from this round's attested head, its first link pinned to the attested
                        predecessor -- so it is the history the WM vouches for right now;
      this device's     from its own stored head -- so it is the history this device holds.

    They must meet at ONE root, and must DIFFER one step above it. Every link on both sides is
    authorised by a holder of this wallet's K_auth, so this is a genuine fork of this wallet's
    own history, not a branch the WM or the host made up -- neither holds K_auth. The WM stays
    an authority on currency and never becomes one on lineage.

    WHY "DIFFER ONE STEP ABOVE". Any state below the real fork point is also common to both
    branches, so meeting at a root alone would let a host name a LOWER fork counter and inflate
    the number of discarded changes on the screen. Requiring the branches to part immediately
    above makes the fork point the latest common state and the count the real one. It also
    refuses a device that is not on a fork at all -- one whose head is on the WM's branch, which
    is `verify_chain`'s case.

    WHAT IT COSTS, and the user decides. Every change this device holds above the fork point is
    discarded. That is the same power `rollback` already hands a hostile WM, gated the same way:
    a hold, and numbers that come only from authenticated data. A change still OFFERED and
    unconfirmed settles as not landed -- its authorisation is not on the WM's branch -- so it stays
    pending and `flush_queue` offers it again on top of the new head. One this device had already
    ADOPTED on the lost branch was settled as landed back then, and is among the discarded count.

    ONE REQUEST, NO STORED CONSENT. `rollback` mints a transition and has to wait for the WM to
    accept it, so it records the user's consent for the adoption that follows. Nothing is minted
    here: the WM's head is already attested in this round, and this handler proves the walk,
    asks, and adopts in one go. There is no consent left lying around to go stale.

    NOT FOR A WM THAT IS BEHIND this device -- ingest refuses that, and `rollback` is the tool.
    """
    from trezor.messages import WardRejoinAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .adopt import adopt, require_attested_round
    from .attest import EMPTY_ROOT, root_or_empty
    from .common import require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root
    from .verify_chain import walk_back, warn_reached_by_revert

    require_initialized()

    # THE WM'S HEAD, from this round's attestation and nothing the host names. Roots arrive in
    # preimage form; the walk and the adoption hold an empty tree as None.
    from_counter, from_root, head_counter, head_root = require_attested_round("rejoin")
    from_root = None if from_root == EMPTY_ROOT else from_root
    head_root = None if head_root == EMPTY_ROOT else head_root

    stored_counter = await get_counter()
    stored_root = await get_root()
    if stored_root is None:
        raise DataError("WARD: no trusted root; nothing to rejoin from")
    stored_root = None if stored_root == EMPTY_ROOT else stored_root

    if head_counter < stored_counter:
        raise DataError("WARD: the WM head is behind this device; use WardRollback")

    fork_counter = msg.fork_counter
    if fork_counter is None:
        raise DataError("WARD: fork_counter is required")
    # Both branches must take at least one step: a fork point at or above either head is not a
    # fork point, and an empty walk has no "one step above" to compare.
    if fork_counter >= stored_counter or fork_counter >= head_counter:
        raise DataError("WARD: the fork point must be below both heads")

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # THE WM'S BRANCH. The first link must begin where the WM said it did, exactly as in
    # `verify_chain`, so the walk starts from the step the WM attested and nowhere else.
    main_root, crossed, reverts, main_above = await walk_back(
        k_auth,
        ward_id,
        head_counter,
        head_root,
        fork_counter,
        expect_from=(from_counter, from_root),
    )

    # THIS DEVICE'S BRANCH, from its own stored head. Nothing pins the first link but the head
    # itself, and nothing needs to: `verify_chain_step_back` refuses any link that does not end
    # at the state being walked from.
    branch_root, _branch_crossed, _branch_reverts, branch_above = await walk_back(
        k_auth,
        ward_id,
        stored_counter,
        stored_root,
        fork_counter,
    )

    if root_or_empty(main_root) != root_or_empty(branch_root):
        raise DataError("WARD: the two branches do not meet at the fork point")
    # Both walks took a step (the bounds above), so both `above` states exist and sit at
    # `fork_counter + 1`. Equal means the branches were still one history there.
    assert main_above is not None and branch_above is not None
    if root_or_empty(main_above[1]) == root_or_empty(branch_above[1]):
        raise DataError("WARD: the branches do not part at the fork point")

    discarded = stored_counter - fork_counter
    await confirm_properties(
        "ward_rejoin",
        "Rejoin shared history",
        [
            ("Currently at", "change #%d" % stored_counter, False),
            ("Last shared", "change #%d" % fork_counter, False),
            ("Rejoining at", "change #%d" % head_counter, False),
            (
                "Discarding",
                "%d change%s" % (discarded, "" if discarded == 1 else "s"),
                False,
            ),
            (
                "Warning",
                "The WARD Manager did not keep changes it had confirmed. Discarded changes cannot be recovered.",
                False,
            ),
        ],
        hold=True,
    )

    # The shared tail. Settling by the WM branch's own links is what leaves this device's lost
    # claims PENDING rather than cleared: none of their authorisations is among them.
    await adopt(head_counter, head_root, landed_commits=crossed)

    if reverts:
        await warn_reached_by_revert(reverts)

    return WardRejoinAck(
        counter=head_counter,
        new_root=head_root,
        discarded=discarded,
        reverts_crossed=reverts,
    )
