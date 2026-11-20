from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardCatchUp, WardCatchUpAck


async def catch_up(msg: WardCatchUp) -> WardCatchUpAck:
    """Follow this wallet's own chain to the head the host names, with no WM, for THIS SESSION.

    The walk runs back from the named head and must land exactly on the stored one, every link
    authorised by a device of this wallet, so the head is genuine and descends from what this
    device holds -- but nothing says it is the latest, or even on the WM's line. Hence reads prove
    against it only in this session and only under the "not proven current" warning, and NOTHING
    IS PERSISTED: moving the stored counter without the WM is what let a host walk a device back
    up a branch the user had discarded (see `WardVerifyChain`'s removed archived anchor).

    A head below the stored counter is an attempt to serve this device an older tree, and is
    refused before any link is asked for.
    """
    from trezor import log
    from trezor.messages import WardCatchUpAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_or_empty, same_root
    from .common import require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root
    from .verify_chain import walk_back

    require_initialized()

    if sync_round.is_online():
        raise DataError("WARD: this session already has a WM-attested head; catch-up is for without one")

    stored_counter = await get_counter()
    stored_root = await get_root()
    to_counter = msg.to_counter
    to_root = msg.to_root or None

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

    reverts = 0
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
        landed, _crossed, reverts, _above = await walk_back(
            await derive_k_auth(),
            await derive_ward_id(),
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

    sync_round.set_provisional(to_counter, root_or_empty(to_root))
    log.info(
        __name__,
        "caught up without the WM: #%d -> #%d (%d revert(s) crossed), this session only, not proven current",
        stored_counter,
        to_counter,
        reverts,
    )
    return WardCatchUpAck(counter=to_counter, reverts_crossed=reverts or None)
