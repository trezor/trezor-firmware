from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRollback, WardRollbackAck


async def rollback(msg: WardRollback) -> WardRollbackAck:
    """Demote the head to a state the host can still serve, with the user's consent.

        (wm_counter, wm_root) -> (wm_counter + 1, recovered_root)   under TAG_REVERT

    Built from the WM's attested head, so one operation covers both a host that cannot rebuild
    the current tree and a WM whose register regressed. The counter still goes forward, so
    stepped-over authorisations stay dead. The target is the host's proposal and is not proven to
    have ever been the head: the user is the authority, and the hold screen shows the depth and
    says so. A fork (WM ahead on another branch) is `WardRejoin`'s.

    Nothing is adopted here. When the new counter does not advance this device, the user's
    consent for this exact transition is recorded so `ingest` and `reconcile` let it back in.
    """
    from trezor.messages import WardRollbackAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_attested
    from .cas import authorise
    from .common import (
        WARNING_UNVERIFIED,
        change_no,
        count_changes,
        require_initialized,
    )
    from .root import get_counter

    require_initialized()

    # The predecessor is the WM's own attested head, the pair it will compare-and-swap on.
    _fc, _fr, wm_counter, wm_root = await verify_attested(msg)

    recovered_root = msg.recovered_root or None
    if recovered_root is not None and len(recovered_root) != 32:
        raise DataError("recovered_root must be 32 bytes")

    stored_counter = await get_counter()
    new_counter = wm_counter + 1

    props = [
        ("Currently at", change_no(stored_counter), False),
        ("Restoring at", change_no(new_counter), False),
    ]
    # Depth from authenticated numbers: an honest recovery is shallow, malice must go deep.
    if new_counter <= stored_counter:
        props.append(("Discarding", count_changes(stored_counter - new_counter), False))
    props += [
        ("Warning", "Discarded changes cannot be recovered.", False),
        ("Target", "Proposed by the host. Not confirmed by the WARD Manager.", False),
        WARNING_UNVERIFIED,
    ]

    await confirm_properties("ward_rollback", "Revert changes", props, hold=True)

    # After the hold, and only when needed: an advancing demotion needs no exemption.
    if new_counter <= stored_counter:
        sync_round.authorise_demotion(
            stored_counter, wm_counter, wm_root, new_counter, recovered_root
        )

    # The head nonce binds this REVERT to this moment: it re-creates an older (counter, root)
    # pair, which would otherwise revive authorisations minted for the earlier occurrence.
    step, advance = await authorise(
        wm_counter, wm_root, new_counter, recovered_root, revert=True
    )
    return WardRollbackAck(
        counter=new_counter,
        new_root=recovered_root,
        auth_commit=step,
        wm_sig=advance,
    )
