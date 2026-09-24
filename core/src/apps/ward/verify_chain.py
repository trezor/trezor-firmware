from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardVerifyChain, WardVerifyChainAck

# How many links one ack may carry. The wire buffer is 8704 bytes and a link costs ~112, so a
# full ack is around 77; this is a sanity bound on a host that pads, not a protocol limit -- the
# walk's real bound is the counter distance, checked below.
_MAX_LINKS_PER_ACK = 128


async def verify_chain(msg: WardVerifyChain) -> WardVerifyChainAck:
    """Adopt the attested head by proving this device's head is an ANCESTOR of it.

    Runs after WardIngestAttestation, in place of WardReconcile. Where reconcile takes the new
    head on the WM's word plus a mac, this additionally establishes that every step between here
    and there was authorised by a device of this wallet and that none was skipped -- which is what
    a device needs after another device wrote while it was away.

    THE WALK RUNS BACKWARDS, AND THAT IS THE SECURITY CONTENT, not an implementation choice.

    Folding FORWARD from this device's head, the `from` end of each link is pinned and the `to`
    end is the host's to choose; the destination is only checked once, at the end. That is enough
    when the whole history arrives in one message, and not enough otherwise -- and it is unsafe
    for a different reason as well: `set_entry` hands out an `auth_commit` on WardLeafAck BEFORE
    knowing whether the write landed, so a host that merely keeps what it is given holds genuine
    links for transitions the WM never accepted. A forward fold follows one onto an orphaned
    branch and nothing recovers from there -- the counter cannot go back, no later chain from the
    real line reconnects to that root, and `rollback` needs an attestation the branch never had.

    Anchored at the attested head and walking BACK, the `to` end of every link is pinned by a
    state already established, ultimately by the WM's signature. Every state the walk reaches is
    therefore an ancestor of a head the WM vouched for, and an orphan cannot enter: the walk asks
    for the link ending at a specific (counter, root), and `verify_chain_step_back` refuses one
    that ends anywhere else before computing its MAC.

    And it removes the ceiling. Links are pulled one ack at a time, so the 8704-byte buffer bounds
    a single WardChainLinkAck instead of the catch-up distance, and a device arbitrarily far
    behind catches up in one workflow. Nothing is persisted until the walk completes, so an
    abandoned walk leaves no head, no latch and nothing to reconcile.

    GAP(ward): multi-device is exercised only through the host ORACLE -- `tests/ward_trie.py`
    serves both the links and the proofs, and no test runs two real devices against one trie.
    Evolu's own history makes a real one possible, because replaying it is exactly how a second
    device catches up: rebuild live state from `evolu_history` to serve proofs, then serve the
    transitions here as WardChainLink to prove descent. The test wants two emulators on one seed:
    A writes, B replays and verifies, and B's derived head must equal A's.
    """
    from trezor.messages import WardVerifyChainAck
    from trezor.wire import DataError

    from .adopt import adopt
    from .attest import root_or_empty
    from .common import require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # THE ANCHOR IS THIS ROUND'S ATTESTATION, and nothing else. The WM attests the whole step in
    # the clear, so both ends come out of the round and the host names none of them -- see
    # `_anchor` for why the archived alternative was removed rather than kept alongside.
    anchor_from_counter, anchor_from_root, anchor_counter, anchor_root = await _anchor(
        msg
    )

    # The baseline is the device's OWN head, not anything the host names. A host-chosen target
    # would let the walk stop at a state this device never reached.
    target_counter = await get_counter()
    target_root = await get_root()

    if anchor_counter < target_counter:
        raise DataError("WARD: the anchored head is behind this device")

    running_counter = anchor_counter
    running_root = anchor_root

    # Every step's authorisation is kept, because it is the precise evidence a queued change
    # landed: a claim filed by `flush_queue` carries the `auth_commit` of its own transition, so
    # matching against this list distinguishes "the head reached N" from "MY change made it N".
    crossed = []
    # Counted, not just accepted. A history containing demotions means changes this device once
    # saw as committed have been undone, and a catch-up that cannot say so has lost the one thing
    # the REVERT tag carries.
    reverts = 0

    # THE FIRST LINK MUST BEGIN WHERE THE WM SAID IT DID -- passed down so the check happens as
    # that link is folded, not after the batch. A host serving several links at once would
    # otherwise walk straight past it.
    expect_from = (anchor_from_counter, anchor_from_root)

    while running_counter > target_counter:
        running_counter, running_root, stepped = await _pull_batch(
            k_auth,
            ward_id,
            running_counter,
            running_root,
            target_counter,
            expect_from,
        )
        expect_from = None
        crossed.extend(stepped[0])
        reverts += stepped[1]

    # WHERE THE WALK ARRIVED MUST BE WHERE THIS DEVICE STANDS. The counter is settled by the loop;
    # the root is not, and without this a walk could descend from some OTHER state that happens to
    # sit at the same counter -- which is precisely a fork.
    if root_or_empty(running_root) != root_or_empty(target_root):
        raise DataError("WARD: the chain does not descend from this device's head")

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "chain: %d links to counter %d, %d of them reverts",
            len(crossed),
            anchor_counter,
            reverts,
        )

    # The shared tail -- settle, persist, latch, close -- see `adopt`. Settling by the
    # transitions actually CROSSED rather than by the counter is what stops a record being
    # cleared because another device's write happened to advance past it.
    await adopt(anchor_counter, anchor_root, landed_commits=crossed)

    if reverts:
        await warn_reached_by_revert(reverts)

    return WardVerifyChainAck(
        counter=anchor_counter, new_root=anchor_root, reverts_crossed=reverts
    )


async def warn_reached_by_revert(reverts: int) -> None:
    """Tell the user the head just adopted was reached by discarding changes.

    INFORMATIONAL, NOT A GATE, and the difference is the whole design of this screen.

    A local `WardRollback` holds to confirm because the device is PERFORMING the demotion and the
    user is choosing it. Here the demotion already happened: a holder of this wallet's K_auth
    issued it behind that very screen, and the WM accepted it. This device is catching up to what
    the wallet already is, not authorising it -- and there is no meaningful refusal on offer,
    because declining would not undo anything, it would only leave this device unable to sync at
    all. A prompt that can only be answered one way is an obstacle, not consent.

    What is NOT informational is the fact itself. Changes this device previously saw as committed
    are gone, and a catch-up that adopts in silence is the one path by which a user's approved
    change disappears with nothing on screen. So: shown after the adoption, once per crossing --
    the head has moved past those transitions, so a later sync does not cross them again.

    A COUNT IS THE WHOLE ANSWER, and that is a decision rather than a shortfall. `WardChainLink`
    carries the transition's endpoints and the tag, never the counter the restored root originally
    belonged to -- `rollback` knows it and puts it on its own screen, not on the link -- so naming
    the discarded entries would mean binding that counter into `auth_commit`'s preimage, since
    anything outside the MAC is forgeable. Weighed and declined: what a user has to act on is that
    the wallet went backwards and by how many steps, and the entries themselves are what the next
    read shows against the restored tree. The same count goes back on `WardVerifyChainAck` for a
    host that wants to say it too.
    """
    from trezor.ui.layouts import show_warning

    # ONE ARGUMENT ONLY. `subheader` is a description on bolt and eckhart but becomes the BUTTON
    # LABEL on delizia, so a sentence passed there reads as a button on one model and as body text
    # on the others. Everything this screen has to say goes in `content`.
    #
    # Literal strings, as everywhere else in WARD -- see the note in `common.py` about translation
    # blobs being pending while the wire shape settles. `rollback`'s own screen is literal too.
    await show_warning(
        "ward_chain_revert",
        "Another device discarded %d change(s). This is now the wallet's state."
        % reverts,
    )


async def _anchor(msg: WardVerifyChain) -> "tuple[int, bytes | None, int, bytes | None]":
    """The step this walk descends from: the head the WM attested THIS ROUND, and its predecessor.

    LIVE ONLY, and the host names nothing: `WardVerifyChain` carries no fields at all. The
    anchor fields are reserved on the wire, so a stale host's are dropped by the decoder rather
    than checked here -- one fewer rule that can be forgotten.

    THERE USED TO BE AN ARCHIVED PATH, and removing it is what this function is really about.
    It let a walk anchor on an attestation the host had KEPT from when some earlier head was
    current, on the reasoning that descent needs only GENUINE ("the WM really held this") and not
    FRESH ("this is the head now"), so such a walk could adopt without claiming currency and
    without latching online.

    IT WAS A WAY TO RAISE THE STORED COUNTER WITH NO FRESHNESS AND NO CONSENT, which defeats
    `WardRecoverCounter`. After an operator lowers the head from 57 to 10 -- a screen the user
    holds to confirm, for the one situation where the WM's register was lost -- a host still
    holding the archived attestation for 57, and the links from 10 up to it, could walk the device
    straight back to 57. `adopt` persists the counter before it decides about latching, so the
    recovery was undone silently, the floor was back above what the WM could attest, and the
    wallet was stranded again with no screen and no WM involvement.

    AND IT WAS NO LONGER BUYING ANYTHING. Its purpose was staged catch-up, from when links
    travelled as one repeated field and the 8704-byte buffer bounded the catch-up DISTANCE. The
    backward walk pulls them one ack at a time, so a device arbitrarily far behind catches up in
    a single workflow -- see the note above. Nothing exercised the archived path either: it had
    no test in the tree.

    The archived attestation itself is not gone. `rollback` still requires one, which is the
    question it genuinely answers -- "was this target EVER the head" -- and there the counter
    moves FORWARD and the user holds to confirm. See `attest.verify_archived_attestation`.

    Returns (from_counter, from_root, to_counter, to_root), the roots in app form.
    """
    from .adopt import require_attested_round
    from .attest import EMPTY_ROOT

    # NOTHING IS READ OFF `msg`, and there is nothing to read: WardVerifyChain carries no fields
    # at all now. The anchor fields are RESERVED on the wire rather than merely unused, so a
    # stale host that still sends them has them dropped by the decoder instead of reaching a
    # check here -- which is the stronger arrangement, since it cannot be forgotten.
    from_counter, from_root, counter, root = require_attested_round("verify against")
    return (
        from_counter,
        None if from_root == EMPTY_ROOT else from_root,
        counter,
        None if root == EMPTY_ROOT else root,
    )


async def _pull_batch(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: "bytes | None",
    target_counter: int,
    expect_from: "tuple | None" = None,
) -> "tuple[int, bytes | None, tuple]":
    """Ask the host for the predecessors of the running head and fold as many as apply.

    ONE REQUEST, ONE ACK, and the request names the exact (counter, root) whose predecessor it
    wants. The host cannot answer with a link ending elsewhere -- that is refused in
    `verify_chain_step_back` before the MAC is computed -- so batching is a transport convenience
    with no security content: sending one link is as correct as sending seventy.

    `expect_from`, given only for the walk's FIRST link, is the predecessor the WM's attestation
    named. Checked here rather than after the batch returns, because a host serving several links
    in one ack would otherwise carry the walk past the one step this binds.
    """
    from trezor.messages import WardChainLinkAck, WardChainRequest
    from trezor.wire import DataError, context

    from .attest import root_or_empty
    from .cas import verify_chain_step_back

    ack = await context.call(
        WardChainRequest(to_counter=running_counter, to_root=running_root),
        expected_type=WardChainLinkAck,
    )

    links = ack.links
    if not links:
        raise DataError("WARD: the host cannot continue the chain")
    if len(links) > _MAX_LINKS_PER_ACK:
        raise DataError("WARD: too many links in one ack")

    crossed = []
    reverts = 0
    for link in links:
        running_counter, running_root, reverted = verify_chain_step_back(
            k_auth,
            ward_id,
            running_counter,
            running_root,
            (
                link.from_counter,
                link.from_root or None,
                link.to_counter,
                link.to_root or None,
                link.auth_commit,
            ),
        )
        # AFTER the MAC verified, never before: an unverified commitment is a host's claim.
        if expect_from is not None:
            want_counter, want_root = expect_from
            expect_from = None
            if running_counter != want_counter or root_or_empty(
                running_root
            ) != root_or_empty(want_root):
                raise DataError(
                    "WARD: the first link does not begin at the attested predecessor"
                )
        crossed.append(link.auth_commit)
        if reverted:
            reverts += 1
        # A host may pad an ack past the target; folding further would walk below this device's
        # head, which is `rollback`'s business and needs the user's consent.
        if running_counter == target_counter:
            break

    return running_counter, running_root, (crossed, reverts)
