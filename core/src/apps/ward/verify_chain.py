from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardVerifyChain, WardVerifyChainAck

# Sanity bound on a padding host (~77 links fit the 8704-byte buffer); the walk's real bound is
# the counter distance.
_MAX_LINKS_PER_ACK = 128


async def verify_chain(msg: WardVerifyChain) -> WardVerifyChainAck:
    """Adopt the attested head by proving this device's head is an ANCESTOR of it.

    The walk runs BACKWARDS from the attested head, so every link's `to` end is pinned by a state
    already established (ultimately by the WM's signature) and an orphaned link -- one a host kept
    from a write the WM never accepted -- cannot enter. Links are pulled one ack at a time, so the
    distance is unbounded; nothing is persisted until the walk completes.
    """
    from trezor.messages import WardVerifyChainAck
    from trezor.wire import DataError

    from .adopt import adopt
    from .attest import same_root
    from .common import require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # Anchored on this round's attestation; the host names nothing.
    anchor_from_counter, anchor_from_root, anchor_counter, anchor_root = attested_step(
        "verify against"
    )

    target_counter = await get_counter()
    target_root = await get_root()

    if anchor_counter < target_counter:
        raise DataError("WARD: the anchored head is behind this device")

    running_root, crossed, reverts, _above = await walk_back(
        k_auth,
        ward_id,
        anchor_counter,
        anchor_root,
        target_counter,
        expect_from=(anchor_from_counter, anchor_from_root),
    )

    # Same counter but a different root is a fork; a WM that lost history is `WardRejoin`'s case.
    if not same_root(running_root, target_root):
        raise DataError(
            "WARD: the chain does not descend from this device's head; if the WM lost history, use WardRejoin"
        )

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "chain: %d links to counter %d, %d of them reverts",
            len(crossed),
            anchor_counter,
            reverts,
        )

    # Settled by the transitions actually crossed, not by the counter.
    await adopt(anchor_counter, anchor_root, landed_commits=crossed)

    if reverts:
        await warn_reached_by_revert(reverts)

    return WardVerifyChainAck(
        counter=anchor_counter, new_root=anchor_root, reverts_crossed=reverts
    )


async def warn_reached_by_revert(reverts: int) -> None:
    """Tell the user the head just adopted was reached by discarding changes.
    Informational, not a gate: the demotion already happened under a hold on another device, and
    declining would only leave this device unable to sync. Shown once per crossing.
    """
    from trezor.ui.layouts import show_warning

    # Content only: `subheader` renders as a button label on delizia.
    await show_warning(
        "ward_chain_revert",
        "Another device discarded %d change(s). This is now the wallet's state."
        % reverts,
    )


def attested_step(what: str) -> "tuple[int, bytes | None, int, bytes | None]":
    """This round's attested step `(from_counter, from_root, to_counter, to_root)`, roots in app
    form (the empty tree as None)."""
    from .adopt import require_attested_round
    from .attest import app_root

    from_counter, from_root, counter, root = require_attested_round(what)
    return from_counter, app_root(from_root), counter, app_root(root)


async def walk_back(
    k_auth: bytes,
    ward_id: bytes,
    start_counter: int,
    start_root: "bytes | None",
    stop_counter: int,
    expect_from: "tuple | None" = None,
) -> "tuple[bytes | None, list, int, tuple | None]":
    """Walk authorised links BACK from `(start_counter, start_root)` down to `stop_counter`,
    pulling them from the host one ack at a time.

    Returns `(root_at_stop, crossed, reverts, above)`: the root reached (the caller compares it),
    every crossed `auth_commit` newest first, the REVERT count, and the `(counter, root)` one
    step above the stop (None if no step was taken). `expect_from` pins the first link's
    predecessor. Each request names the exact `(counter, root)` wanted and
    `verify_chain_step_back` refuses a link ending elsewhere, so batching has no security content.
    The walk must land EXACTLY on `stop_counter`: roots repeat, so a batch link jumping over the
    stop could otherwise "arrive" at a state the walk never passed through.
    """
    from trezor.messages import WardChainLinkAck, WardChainRequest
    from trezor.wire import DataError, context

    from .attest import same_root
    from .cas import link_of, verify_chain_step_back

    counter, root = start_counter, start_root
    crossed = []
    reverts = 0
    above = None
    while counter > stop_counter:
        ack = await context.call(
            WardChainRequest(to_counter=counter, to_root=root),
            expected_type=WardChainLinkAck,
        )
        if not ack.links:
            raise DataError("WARD: the host cannot continue the chain")
        if len(ack.links) > _MAX_LINKS_PER_ACK:
            raise DataError("WARD: too many links in one ack")
        for link in ack.links:
            above = (counter, root)
            counter, root, reverted = verify_chain_step_back(
                k_auth, ward_id, counter, root, link_of(link)
            )
            # AFTER the MAC verified, never before: an unverified commitment is a host's claim.
            if expect_from is not None:
                if counter != expect_from[0] or not same_root(root, expect_from[1]):
                    raise DataError(
                        "WARD: the first link does not begin at the attested predecessor"
                    )
                expect_from = None
            crossed.append(link.auth_commit)
            if reverted:
                reverts += 1
            # Never fold below the stop; overshooting is refused below.
            if counter <= stop_counter:
                break
    if counter != stop_counter:
        raise DataError("WARD: the chain does not land on counter %d" % stop_counter)
    return root, crossed, reverts, above
