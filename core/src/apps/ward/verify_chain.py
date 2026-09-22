from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardVerifyChain, WardVerifyChainAck


async def verify_chain(msg: WardVerifyChain) -> WardVerifyChainAck:
    """Adopt the attested head by proving it DESCENDS from the head this device holds.

    Runs after WardIngestAttestation, in place of WardReconcile. Where reconcile takes the
    new head on the WM's word plus a mac, this additionally establishes that every step
    between here and there was authorised by a device of this wallet and that none was
    skipped -- which is what a device needs after another device wrote while it was away.

    GAP(ward): multi-device is exercised only through the host ORACLE -- `tests/ward_trie.py`
    serves both the links and the proofs, and no test runs two real devices against one trie.
    Evolu's own history makes a real one possible, because replaying it is exactly how a
    second device catches up: rebuild live state from `evolu_history` to serve proofs, then
    feed the transitions here as WardChainLink to prove descent. Both halves come from one
    source rather than two that can disagree -- a history row carries the leaf and the counter,
    a link carries the roots and the auth_commit the device issued alongside it. The test wants
    two emulators on one seed: A writes, B replays and verifies, and B's derived head must
    equal A's.

    The two guarantees are complementary and both are required: the chain gives DESCENT,
    the attestation gives CURRENCY, and they are joined by demanding the chain end exactly
    at the attested counter with a root that reproduces the attested mac. Either alone is
    forgeable in a way the pair is not -- a chain to some genuine older head, or an
    attestation of a head reached by a fork.
    """
    from trezor.messages import WardVerifyChainAck
    from trezor.wire import DataError

    from .adopt import adopt, require_attested_round, verify_head_mac
    from .attest import root_mac
    from .cas import verify_chain_step
    from .common import require_initialized
    from .keys import derive_k_auth, derive_k_mac, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    # WHICH HEAD THIS BATCH ENDS AT. Normally the one attested in this round -- the live,
    # nonce-bound answer to "what is current". But a device far behind cannot express its
    # catch-up in one message: links are an unchunked repeated field in an 8704-byte buffer and
    # a link costs ~112 bytes, so about 77 fit. Such a device instead walks in batches, each
    # terminating at an ARCHIVED head whose attestation the host kept.
    #
    # The archived form NEVER decides currency -- see `attest.verify_archived_attestation`. It
    # says only that the WM once held this head, which is exactly what stops a batch being
    # walked onto a fork: descent alone cannot tell one branch from another.
    staged = msg.wm_signature is not None
    # The live attested head is read either way: for an ordinary batch it is the target, and for
    # a staged one it is the CEILING -- a batch may stop short of the current head but never past
    # it.
    live_counter, live_mac = require_attested_round("verify against")

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()
    k_mac = await derive_k_mac()

    # The baseline is the device's OWN head, not anything the host names. A host-chosen
    # starting point would let the walk begin at a state this device never reached.
    running_counter = await get_counter()
    running_root = await get_root()

    # Every step's authorisation is kept, because it is the precise evidence a queued change
    # landed: a claim filed by `flush_queue` carries the `auth_commit` of its own transition, so
    # matching against this list distinguishes "the head reached N" from "MY change made it N".
    crossed = []
    # Counted, not just accepted. A history containing demotions means changes this device once
    # saw as committed have been undone, and a catch-up that cannot say so has lost the one thing
    # the REVERT tag carries.
    reverts = 0
    for link in msg.links:
        running_counter, running_root, reverted = verify_chain_step(
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

    if __debug__:
        from trezor import log

        log.debug(
            __name__, "chain: %d links, %d of them reverts", len(msg.links), reverts
        )

    if staged:
        # THE TARGET IS WHERE THE FOLD ARRIVED, and the device computes its mac itself rather
        # than being told one -- `root_mac` over the running head. So a host cannot name a
        # counter or a mac at all here; it can only supply a signature, which either covers what
        # the fold produced or does not.
        counter = running_counter
        mac = root_mac(k_mac, ward_id, running_counter, running_root)
        await _check_staged_target(
            ward_id, counter, mac, live_counter, msg, await get_counter()
        )
    else:
        counter, mac = live_counter, live_mac
        if running_counter != counter:
            raise DataError("chain does not end at the attested counter")
        # ...and the state it ends in must be the state that was attested. Without this the
        # chain could authorise a walk to a head the WM never vouched for.
        await verify_head_mac(counter, mac, running_root, subject="chain end")

    # The shared tail -- settle, persist, and (unless staged) latch and close -- see `adopt`.
    # This route settles by the transitions it actually CROSSED rather than by the counter, so it
    # does not clear a record whose change another device's write happened to advance past.
    await adopt(counter, running_root, landed_commits=crossed, staged=staged)

    return WardVerifyChainAck(counter=counter, new_root=running_root)


async def _check_staged_target(
    ward_id: bytes,
    counter: int,
    mac: bytes,
    live_counter: int,
    msg: WardVerifyChain,
    stored: int,
) -> None:
    """May this batch stop here, and did the WM ever hold this head?

    `counter` and `mac` are the device's OWN -- where its fold arrived, and the mac it computed
    over that state. The host supplies only a signature, so it cannot name a destination; it can
    only fail to have one for the destination the links produced.

    THREE RULES, each closing a distinct way of abusing a replayed attestation:

      progress -- the target must be above our stored head. Below it would be a demotion, which
        is `WardRollback`'s business and needs the user's consent;
      a ceiling -- not above the head attested in this round, or a batch could adopt something
        the WM has not reached. Neither existing rule covers this range: `ingest` refuses
        anything under the floor and `recover` refuses anything not going backwards, so an
        intermediate is today accepted by no path at all;
      the WM really held it -- the archived signature over (ward_id, counter, mac). Unforgeable,
        so the host can only choose among heads that genuinely existed, and `root_mac` binds the
        counter so the pair admits exactly one root.
    """
    from trezor.wire import DataError

    from .attest import verify_archived_attestation

    nonce = msg.nonce
    signature = msg.wm_signature
    if nonce is None or signature is None:
        raise DataError("a staged batch needs the archived attestation for its target")

    if counter <= stored:
        raise DataError("a staged target must be ahead of this device's head")
    if counter > live_counter:
        raise DataError("a staged target cannot be ahead of the attested head")

    if not verify_archived_attestation(
        ward_id, nonce, counter, mac, msg.timestamp or 0, signature
    ):
        raise DataError("the WM never attested this staged target as its head")
