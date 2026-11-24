from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import (
        WardChainLink,
        WardRollback,
        WardRollbackAck,
    )


async def rollback(msg: WardRollback) -> WardRollbackAck:
    """Restore a state on the wallet's verified history, with the user's consent.

        (wm_counter, wm_root) -> (wm_counter + 1, recovered_root)   under TAG_REVERT

    The revert extends the WM's attested head. If the WM is behind, its head must be
    an ancestor of the device's stored head, and the target can also be the device's
    own state. The counter and root of the target are checked before confirmation.

    Nothing is adopted here. When the new counter does not advance this device, the user's
    consent for this exact transition is recorded so `ingest` and `reconcile` let it back in.
    """
    from trezor.messages import WardChainLinkAck, WardChainRequest, WardRollbackAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError, context

    from . import round as sync_round
    from .adopt import verify_attested
    from .attest import NONCE_LENGTH, app_root, same_root, verify_attestation
    from .cas import authorise
    from .common import (
        change_no,
        count_changes,
        require_initialized,
    )
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root
    from .verify_chain import walk_back

    require_initialized()

    # The predecessor is the WM's own attested head, the pair it will compare-and-swap on.
    from_counter, from_root, wm_counter, wm_root = await verify_attested(msg)

    recovered_counter = msg.recovered_counter
    if recovered_counter is None:
        raise DataError("WARD: the recovery target counter is required")
    recovered_root = msg.recovered_root or None
    if recovered_root is not None and len(recovered_root) != 32:
        raise DataError("recovered_root must be 32 bytes")

    stored_counter = await get_counter()
    stored_root = await get_root()
    if stored_counter and stored_root is None:
        raise DataError("WARD: no trusted device head")
    if wm_counter == 0xFFFFFFFF:
        raise DataError("WARD: no counter available for the revert")
    new_counter = wm_counter + 1

    wm_behind = wm_counter < stored_counter
    anchor_counter = stored_counter if wm_behind else wm_counter
    anchor_root = stored_root if wm_behind else wm_root
    if recovered_counter > anchor_counter:
        raise DataError("WARD: the recovery target is above the verified head")
    if not wm_behind and recovered_counter == anchor_counter:
        raise DataError("WARD: the recovery target must precede the WM head")

    k_auth = await derive_k_auth()
    ward_id = await derive_ward_id()
    use_live = not wm_behind

    async def pull(request: WardChainRequest) -> WardChainLinkAck:
        request.with_acceptance = True
        return await context.call(request, expected_type=WardChainLinkAck)

    def verify_acceptance(link: WardChainLink) -> None:
        # Every accepted transition raises the WM's counter, so within one register history the
        # (counter, root) ends that walk_back already pinned name one accepted step. A register
        # that went back can repeat a pair; see docs/ward/gaps.md.
        nonlocal use_live
        if use_live:
            # walk_back checked the exact predecessor from the fresh attestation.
            use_live = False
            return
        receipt = link.acceptance
        if (
            receipt is None
            or receipt.nonce is None
            or len(receipt.nonce) != NONCE_LENGTH
            or receipt.timestamp is None
            or receipt.wm_signature is None
            or not verify_attestation(
                ward_id,
                receipt.nonce,
                link.from_counter,
                link.from_root or None,
                link.to_counter,
                link.to_root or None,
                receipt.timestamp,
                receipt.wm_signature,
            )
        ):
            raise DataError(
                "WARD: missing or invalid WM acceptance for rollback history"
            )
        if wm_behind and link.to_counter == wm_counter and (
            link.from_counter != from_counter
            or not same_root(link.from_root or None, from_root)
        ):
            # The WM's live attestation names the step into its restored head; this device's
            # history must reach that head by the same step.
            raise DataError("WARD: the restored WM head has a different predecessor")

    # Check both checkpoints on one descent. Restarting at the anchor would let
    # the host change which inbound links it reports for already verified states.
    ancestor_counter = wm_counter if wm_behind else stored_counter
    ancestor_root = wm_root if wm_behind else stored_root
    expected_from = None if wm_behind else (from_counter, from_root)
    cursor_counter, cursor_root = anchor_counter, anchor_root
    checkpoints = [ancestor_counter, recovered_counter]
    if wm_behind and wm_counter:
        checkpoints.append(from_counter)
    for checkpoint in sorted(checkpoints, reverse=True):
        if checkpoint < cursor_counter:
            cursor_root, _, _, _ = await walk_back(
                k_auth,
                ward_id,
                cursor_counter,
                cursor_root,
                checkpoint,
                expect_from=expected_from,
                collect_commits=False,
                pull=pull,
                verify_acceptance=verify_acceptance,
            )
            cursor_counter = checkpoint
            expected_from = None
        if checkpoint == ancestor_counter and not same_root(cursor_root, ancestor_root):
            raise DataError("WARD: the WM and device heads are on different branches")
        if checkpoint == recovered_counter and not same_root(
            cursor_root, recovered_root
        ):
            raise DataError("WARD: recovery target does not match the verified history")
        if checkpoint == recovered_counter:
            recovered_root = app_root(cursor_root)

    changes = anchor_counter - recovered_counter
    props = [
        ("This device", change_no(stored_counter), False),
        ("WARD Manager", change_no(wm_counter), False),
        ("Restore state from", change_no(recovered_counter), False),
        ("New head", change_no(new_counter), False),
        ("Changes after target", count_changes(changes), False),
    ]
    if changes:
        props.append(
            (
                "Warning",
                "Changes after the target are removed from the active state.",
                False,
            )
        )

    await confirm_properties("ward_rollback", "Revert changes", props, hold=True)

    # After the hold, and only when needed: an advancing demotion needs no exemption.
    if new_counter <= stored_counter:
        sync_round.authorise_demotion(
            stored_counter, wm_counter, wm_root, new_counter, recovered_root
        )

    # A REVERT carries an older root under a new counter, so its pair is new. It is bound to this
    # round's nonce, and the WM's compare-and-swap on (wm_counter, wm_root) lets it move the head
    # once.
    step, advance = await authorise(
        wm_counter, wm_root, new_counter, recovered_root, revert=True
    )
    return WardRollbackAck(
        counter=new_counter,
        new_root=recovered_root,
        auth_commit=step,
        wm_sig=advance,
    )
