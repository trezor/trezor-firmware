from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardReconcile, WardReconcileAck


async def reconcile(msg: WardReconcile) -> WardReconcileAck:
    """Adopt the attested head, having folded the single link that produced it.


    The host supplies only the `auth_commit`; all operands come from the attested round. The
    predecessor must be this device's head, so the head moves by exactly one link (a write or a
    batch of up to MAX_BATCH changes), stays put, or comes down by an approved demotion. Gaps go
    to `verify_chain`, which proves every intervening link.
    """
    from trezor.messages import WardReconcileAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import adopt, require_attested_round, verify_inbound_link
    from .attest import app_root, same_root
    from .cas import MAX_BATCH
    from .common import require_initialized
    from .root import get_counter, get_root

    require_initialized()

    from_counter, from_root, counter, root = require_attested_round("reconcile")

    # Checked in preimage form, before the empty tree is normalised to None.
    reverted = await verify_inbound_link(
        from_counter, from_root, counter, root, msg.auth_commit
    )

    root = app_root(root)

    stored_counter = await get_counter()
    stored_root = await get_root()

    if sync_round.demotion_matches(
        stored_counter, from_counter, from_root, counter, root
    ):
        # The demotion the user approved; its link was still verified above.
        sync_round.clear_demotion()

    elif counter == stored_counter:
        if stored_root is not None and not same_root(stored_root, root):
            raise DataError("attested counter matches but the root differs")

    elif (
        stored_counter + 1 <= counter <= stored_counter + MAX_BATCH
        and from_counter == stored_counter
        and same_root(from_root, stored_root)
    ):
        # One link from this device's head: a single write or a single batch.
        pass

    elif counter == stored_counter + 1:
        raise DataError("WARD: the attested step does not start at this device's head")

    else:
        raise DataError(
            "WARD: reconcile adopts at most one step; use WardVerifyChain to catch up"
        )

    # The link itself settles the claim it was filed for, not the counter.
    await adopt(counter, root, landed_commits=[msg.auth_commit] if msg.auth_commit else None)

    if reverted:
        from .verify_chain import warn_reached_by_revert

        await warn_reached_by_revert(1)

    return WardReconcileAck(counter=counter, new_root=root)
