from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardCatchUp, WardCatchUpAck


async def catch_up(msg: WardCatchUp) -> WardCatchUpAck:
    """Follow this wallet's own chain to a head the host names, with no WM.

    The walk runs back from the named head and must land exactly on the stored head, every link
    authorised by a device of this wallet, so the head is genuine and descends from what this
    device holds. What else is required, and whether the head is kept, depends on the deployment:

    WITH A WM (the default build), the head must be the `to` end of a CACHED attestation, verified
    over the round nonce the host supplies: the WM really did hold it, at `timestamp`. Neither that
    nor the walk says it is the latest, or still on the WM's line, so by default reads prove
    against it only in THIS SESSION, under the warning that they do not reflect changes since
    `timestamp`, nor reverts, and NOTHING IS PERSISTED: moving the stored counter without a live
    attestation is what let a host walk a device back up a branch the user had discarded (see
    `WardVerifyChain`'s removed archived anchor). The user may allow persisting for this wallet
    (`WardSetPersistWithoutWm`), accepting that a device which missed a revert can be walked up the
    branch it removed, and then needs a `WardRollback` once the WM is back.

    The signed date is retained for display. Only the authenticated history orders heads.

    WITHOUT A WM (the MVP build) there is nothing to attest a head, so the chain alone decides and
    the head is always persisted: it is how the stored head moves at all, writes included.

    A head below the stored counter is an attempt to serve this device an older tree, and is
    refused before anything else is checked.
    """
    import storage.ward as ward_store
    from trezor import log
    from trezor.messages import WardCatchUpAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import persist_caught_up
    from .attest import NONCE_LENGTH, root_or_empty, same_root, verify_attestation
    from .common import has_wm, require_initialized
    from .keys import derive_k_auth, derive_wallet_id, derive_ward_id
    from .root import get_counter, get_root
    from .verify_chain import walk_back

    require_initialized()

    if sync_round.is_online():
        raise DataError("WARD: this session already has a WM-attested head; catch-up is for without one")

    stored_counter = await get_counter()
    stored_root = await get_root()
    to_counter = msg.to_counter
    to_root = msg.to_root or None
    ward_id = await derive_ward_id()

    if to_counter < stored_counter:
        log.info(
            __name__,
            "catch-up REFUSED: the host offered head #%d, older than the stored #%d",
            to_counter,
            stored_counter,
        )
        raise DataError(
            "WARD: the host offered head #%d, older than this device's #%d"
            % (to_counter, stored_counter)
        )
    if stored_root is None and stored_counter != 0:
        raise DataError("WARD: no trusted root to catch up from")

    timestamp = None
    if has_wm():
        # The cached attestation of the named head. Checked before any link is asked for.
        if (
            msg.nonce is None
            or len(msg.nonce) != NONCE_LENGTH
            or msg.from_counter is None
            or msg.timestamp is None
            or msg.wm_signature is None
        ):
            raise DataError("WARD: catch-up needs the WM's attestation of the named head")
        if not verify_attestation(
            ward_id,
            msg.nonce,
            msg.from_counter,
            msg.from_root or None,
            to_counter,
            to_root,
            msg.timestamp,
            msg.wm_signature,
        ):
            log.info(__name__, "catch-up REFUSED: head #%d carries no valid WM attestation", to_counter)
            raise DataError("WARD: the WM never attested that head")
        timestamp = msg.timestamp

    reverts = 0
    crossed = []
    if to_counter == stored_counter:
        if not same_root(to_root, stored_root):
            log.info(
                __name__,
                "catch-up REFUSED: another root at the stored counter #%d",
                stored_counter,
            )
            raise DataError("WARD: the host offered another tree at this device's own counter")
    else:
        # Never adopted anything: the only state at counter 0 is the empty tree.
        landed, crossed, reverts, _above = await walk_back(
            await derive_k_auth(),
            ward_id,
            to_counter,
            to_root,
            stored_counter,
        )
        if not same_root(landed, stored_root):
            log.info(
                __name__,
                "catch-up REFUSED: head #%d does not descend from the stored #%d",
                to_counter,
                stored_counter,
            )
            raise DataError("WARD: that head does not descend from this device's head")

    persist = not has_wm() or ward_store.get_setting(
        await derive_wallet_id(), ward_store.SETTING_PERSIST_WITHOUT_WM
    )
    if persist:
        await persist_caught_up(to_counter, to_root, crossed, timestamp)
    else:
        assert timestamp is not None
        sync_round.set_provisional(to_counter, root_or_empty(to_root), timestamp)
    log.info(
        __name__,
        "caught up without the WM: #%d -> #%d (%d revert(s) crossed), attested at %s, %s",
        stored_counter,
        to_counter,
        reverts,
        "-" if timestamp is None else str(timestamp),
        "persisted" if persist else "this session only",
    )
    return WardCatchUpAck(
        counter=to_counter, reverts_crossed=reverts or None, persisted=persist
    )
