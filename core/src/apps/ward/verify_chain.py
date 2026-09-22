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
    from .keys import derive_k_auth, derive_k_mac, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()
    k_mac = await derive_k_mac()

    # THE ANCHOR'S ROOT comes from the host, and is accepted only because it reproduces a mac
    # the WM signed. `root_mac` binds the counter, so an attested (counter, mac) admits exactly
    # one root -- the same binding `reconcile` rests on, applied at the far end of a walk rather
    # than in place of one. Which KIND of anchor it is decides one thing only: whether this walk
    # may claim CURRENCY at the end. See `_anchor`.
    anchor_root = msg.head_root or None
    anchor_counter, archived = await _anchor(ward_id, k_mac, anchor_root, msg)

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

    while running_counter > target_counter:
        running_counter, running_root, stepped = await _pull_batch(
            k_auth,
            k_mac,
            ward_id,
            running_counter,
            running_root,
            target_counter,
        )
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
            "chain: %d links to counter %d, %d of them reverts, archived=%s",
            len(crossed),
            anchor_counter,
            reverts,
            archived,
        )

    # The shared tail -- settle, persist, and (unless archived) latch and close -- see `adopt`.
    # Settling by the transitions actually CROSSED rather than by the counter is what stops a
    # record being cleared because another device's write happened to advance past it.
    await adopt(
        anchor_counter, anchor_root, landed_commits=crossed, current=not archived
    )

    if reverts:
        await _warn_reached_by_revert(reverts)

    return WardVerifyChainAck(
        counter=anchor_counter, new_root=anchor_root, reverts_crossed=reverts
    )


async def _warn_reached_by_revert(reverts: int) -> None:
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


async def _anchor(
    ward_id: bytes,
    k_mac: bytes,
    head_root: "bytes | None",
    msg: WardVerifyChain,
) -> "tuple[int, bool]":
    """The head this walk descends to, and whether it is a CURRENT one.

    An anchor has two properties and they come apart:

      GENUINE -- the WM really held this head. An ancestor of a head the WM held is on the
        authoritative line, so this is what makes descent mean anything, and an ARCHIVED
        attestation carries it in full;
      FRESH -- this head is the head NOW. Only this round's nonce carries it, because
        `round.clear` zeroes the slot and the device cannot tell a nonce it minted last week
        from arbitrary bytes.

    Descent needs only the first, which is why a walk can be anchored on an archive and run with
    no round at all. Currency needs the second, and `mark_online` is what must not be reached
    without it -- `round.is_online` decides whether reads are served from the backend, and a host
    replaying an old attestation must never be able to freeze a device at an old head while those
    values are presented as current. That is the eclipse the nonce exists to close, and the
    returned flag is what keeps this path out of it.

    EITHER WAY THE HOST NAMES NO MAC. On the live path the mac is the round's, and `head_root` is
    bound to it. On the archived path the device computes the mac from `head_root` itself, so the
    host can only fail to hold a signature over what the device derived. Both reduce to the same
    statement: the WM signed a mac, and exactly one root reproduces it at that counter.

    Returns (counter, archived).
    """
    from trezor.wire import DataError

    from .adopt import require_attested_round, verify_head_mac
    from .attest import root_mac, verify_archived_attestation

    nonce = msg.nonce
    signature = msg.wm_signature
    if nonce is None and signature is None:
        counter, mac = require_attested_round("verify against")
        await verify_head_mac(counter, mac, head_root, subject="chain anchor")
        return counter, False

    if nonce is None or signature is None:
        raise DataError("WARD: an archived anchor needs both a nonce and a signature")

    counter = msg.anchor_counter
    if counter is None:
        raise DataError("WARD: an archived anchor needs the counter it attests")

    mac = root_mac(k_mac, ward_id, counter, head_root)
    if not verify_archived_attestation(
        ward_id, nonce, counter, mac, msg.timestamp or 0, signature
    ):
        raise DataError("WARD: the WM never attested this head")
    return counter, True


async def _pull_batch(
    k_auth: bytes,
    k_mac: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: "bytes | None",
    target_counter: int,
) -> "tuple[int, bytes | None, tuple]":
    """Ask the host for the predecessors of the running head and fold as many as apply.

    ONE REQUEST, ONE ACK, and the request names the exact (counter, root) whose predecessor it
    wants. The host cannot answer with a link ending elsewhere -- that is refused in
    `verify_chain_step_back` before the MAC is computed -- so batching is a transport convenience
    with no security content: sending one link is as correct as sending seventy.
    """
    from trezor.messages import WardChainLinkAck, WardChainRequest
    from trezor.wire import DataError, context

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
            k_mac,
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
        # After the step verified, never before: an unverified commitment is a host's claim.
        crossed.append(link.auth_commit)
        if reverted:
            reverts += 1
        # A host may pad an ack past the target; folding further would walk below this device's
        # head, which is `rollback`'s business and needs the user's consent.
        if running_counter == target_counter:
            break

    return running_counter, running_root, (crossed, reverts)
