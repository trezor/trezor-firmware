from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRejoin, WardRejoinAck


async def rejoin(msg: WardRejoin) -> WardRejoinAck:
    """Rejoin the WM's history after it lost the branch this device stands on.

    For a WM whose register was restored below this device's head and has since moved on. Both
    branches are walked back to `fork_counter` under K_auth -- the WM's from this round's attested
    head, this device's from its own -- and must meet at one root and differ one step above it,
    so the fork point is the latest common state and the discard count on the hold screen is
    real. Unconfirmed offered changes settle as not landed and are offered again.
    """
    from trezor.messages import WardRejoinAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .adopt import adopt
    from .attest import EMPTY_ROOT, root_or_empty
    from .common import require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root
    from .verify_chain import attested_step, walk_back, warn_reached_by_revert

    require_initialized()

    from_counter, from_root, head_counter, head_root = attested_step("rejoin")

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
    if fork_counter >= stored_counter or fork_counter >= head_counter:
        raise DataError("WARD: the fork point must be below both heads")

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    main_root, crossed, reverts, main_above = await walk_back(
        k_auth,
        ward_id,
        head_counter,
        head_root,
        fork_counter,
        expect_from=(from_counter, from_root),
    )

    branch_root, _branch_crossed, _branch_reverts, branch_above = await walk_back(
        k_auth,
        ward_id,
        stored_counter,
        stored_root,
        fork_counter,
    )

    if root_or_empty(main_root) != root_or_empty(branch_root):
        raise DataError("WARD: the two branches do not meet at the fork point")
    # Compared as (counter, root) states: a batch on one branch puts `above` at another counter.
    assert main_above is not None and branch_above is not None
    if main_above[0] == branch_above[0] and root_or_empty(
        main_above[1]
    ) == root_or_empty(branch_above[1]):
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

    # Settled by the WM branch's links, so this branch's lost claims stay pending.
    await adopt(head_counter, head_root, landed_commits=crossed)

    if reverts:
        await warn_reached_by_revert(reverts)

    return WardRejoinAck(
        counter=head_counter,
        new_root=head_root,
        discarded=discarded,
        reverts_crossed=reverts,
    )
