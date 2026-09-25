"""What every route into a new head has in common.

FOUR HANDLERS TOUCH THE SYNC ROUND, in two pairs, and each pair duplicated a sequence:

    ingest / recover           verify the WM's attestation against this round's nonce, then apply
                               opposite counter rules to it -- forward-only for the ordinary path,
                               backwards-only for the recovery one.

    reconcile / verify_chain    take the attested root, settle queued writes against it, persist
                               it, and latch the session online. They differ ONLY in how much of
                               the history they prove: reconcile folds the SINGLE link into the
                               attested head; verify_chain anchors there and walks authorised
                               links BACK to the device's own, proving every step between.

Factored out because the sequences are security-relevant and were drifting: the online latch was
added to `reconcile` and forgotten in `verify_chain`, and the check that a root was actually stored
had to be added to both. A third route -- a device-initiated sync over a service channel -- will
want the same tail, and copying it a third time is how the next asymmetry gets introduced.

WHAT IS DELIBERATELY NOT FACTORED. The route-specific proof stays with its handler: reconcile's
"one counter names one state" comparison and verify_chain's backward walk are what distinguish them,
and hiding either behind a shared helper would make the weaker route look like the stronger one.
The ORDER of the remaining steps is load-bearing rather than incidental, which is why `verify_inbound_link`
and `adopt` are separate: reconcile has a check that must run between them.
"""


async def verify_round_attestation(
    from_counter: "int | None",
    from_root: "bytes | None",
    from_head_nonce: "bytes | None",
    to_counter: "int | None",
    to_root: "bytes | None",
    to_head_nonce: "bytes | None",
    timestamp: int,
    signature: "bytes | None",
) -> "tuple[int, bytes, int, bytes]":
    """Check a WM attestation against the OPEN round, and return the transition it names.

    Verifies only that some authority the device trusts said this STEP is current, and said it in
    answer to THIS round's nonce. Adopts nothing, and applies NO counter rule, because the two
    callers want opposite ones: `ingest` refuses anything older than the stored floor, `recover`
    refuses anything that is not older. Putting either rule here would let the other route reach
    the wrong one.

    TAKES VALUES, NOT A MESSAGE. It used to be duck-typed over `WardIngestAttestation`,
    `WardRecoverCounter`, `WardSyncResponse` and `WardPublishAck` -- four messages that had to
    keep identical field names forever, silently, or this would read `None` off one of them and
    fail as "verification failed". Two of those callers hold the `from` end in local scope and
    never had it on the wire at all, which is what made the duck-typing untenable rather than
    merely fragile.

    RETURNS BOTH ROOTS IN PREIMAGE FORM -- EMPTY_ROOT for the empty tree -- since that is what the
    signature covered and what `round.set_attested` must store for a later recomputation.

    LATCHES THE WM'S HEAD -- `(to_counter, to_root, to_head_nonce)` -- as a side effect, and this
    is the only place that does. All three are covered by the signature, so by the time this
    returns they are WM-vouched facts rather than host claims, and every route that will later
    mint a `cas.wm_sig` passes through here first. Latched even when the caller goes on to refuse
    the attestation for its own reasons: the WM's state is not our verdict on it, and holding a
    stale nonce only costs a write the WM would reject anyway. NOT returned, because nothing
    should be threading it through call chains -- callers ask `round.require_head_nonce()`.

    THE TWO CONTINUITY RULES, which are what naming BOTH ends of the head nonce buys. The attested
    edge is `(from_counter, from_root, from_head_nonce) -> (to_counter, to_root, to_head_nonce)`,
    and `from_head_nonce` is the nonce the WM CONSUMED accepting it -- so the edge names the
    transition OCCURRENCE, not merely the transition. Against the head this device last saw:

      R1, THE ADVANCE. If the attested `from` end is that head, the WM accepted a transition out
      of it, and the nonce it consumed must be the one this device latched for it. This is how a
      device learns that the authorisation IT minted is the one that was spent, rather than that
      some occurrence of the same transition landed -- a distinction with content, because roots
      repeat and a revert re-creates an older pair by construction.

      R2, THE STANDSTILL. If the attested `to` end is that head, the WM has not moved since --
      every transition advances the counter by one, so a head that did not move accepted nothing
      and cannot have rotated. A different nonce there means the register moved without a
      transition: a restore, a failover onto a stale replica, a fork. This is the one case where
      the device can catch a broken WM by itself, and it catches the restore that lands exactly
      where this device is standing -- the most likely one.

    NEITHER RULE IS A COUNTER RULE. They say nothing about whether the head may be adopted, only
    that the WM's register is continuous with what this device already saw, so they are the same
    for every caller and belong here rather than in one of them. When the attested step touches
    neither end of the latched head the WM has moved further than this device can account for
    locally, both rules stand down, and `verify_chain` is what proves the gap.

    ACROSS A SESSION THEY DO NOT APPLY AT ALL: the latch is session-scoped, so a fresh session
    starts with nothing to compare against. See `round.set_wm_head`.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_or_empty, verify_attestation
    from .cas import NO_HEAD_NONCE
    from .keys import derive_ward_id

    ctx = sync_round.get()
    if ctx is None:
        raise DataError("no sync round in progress")
    _state, nonce, _fc, _fr, _tc, _tr = ctx

    if to_counter is None or from_counter is None or signature is None:
        raise DataError("both ends of the transition and wm_signature are required")
    if (
        from_head_nonce is None
        or len(from_head_nonce) != 32
        or to_head_nonce is None
        or len(to_head_nonce) != 32
    ):
        raise DataError("WARD: both attested WM head nonces must be 32 bytes")

    # NO LIVE HEAD MAY CARRY THE ENROLMENT CONSTANT, at either end. `cas.NO_HEAD_NONCE` is only
    # what `head_init_sig` is signed under; a WM that accepts an enrolment draws a real `N0`
    # before it attests anything. Seeing it here means the WM never drew one -- and a head left at
    # a CONSTANT would make the first write after genesis replayable into any future re-enrolment,
    # which is the one recurrence the nonce exists to prevent. See `cas.NO_HEAD_NONCE`.
    if NO_HEAD_NONCE in (from_head_nonce, to_head_nonce):
        raise DataError("WARD: the attested WM head carries the enrolment nonce")
    for r in (from_root, to_root):
        if r is not None and len(r) != 32:
            raise DataError("attested roots must be 32 bytes")

    # THE STEP MUST BE ONE STEP, checked on the WM's own claim rather than on the host's link.
    # Genesis is the exception and the only one: counter 0 has no predecessor, so it attests
    # itself -- see `attest.attestation_preimage`.
    if to_counter == 0:
        if from_counter != 0 or root_or_empty(from_root) != root_or_empty(to_root):
            raise DataError("WARD: counter 0 must attest itself")
        # Nothing produced genesis, so nothing was consumed to reach it -- the same reason the
        # roots are equal at both ends.
        if from_head_nonce != to_head_nonce:
            raise DataError("WARD: counter 0 consumed no head nonce")
    elif to_counter != from_counter + 1:
        raise DataError("WARD: an attested transition advances the counter by exactly one")
    elif from_head_nonce == to_head_nonce:
        # A real step consumes one nonce and mints another. Equal ends would be a WM that did not
        # rotate, which is the failure the whole construction rests on not happening.
        raise DataError("WARD: an attested transition must rotate the WM head nonce")

    if not verify_attestation(
        await derive_ward_id(),
        nonce,
        from_counter,
        from_root,
        from_head_nonce,
        to_counter,
        to_root,
        to_head_nonce,
        timestamp,
        signature,
    ):
        raise DataError("WM attestation verification failed")

    # CONTINUITY, against the head this device last saw the WM at -- see the two rules above.
    # Checked only after the signature, so what is being compared is a WM-vouched value.
    seen = sync_round.wm_head()
    if seen is not None:
        seen_counter, seen_root, seen_nonce = seen
        if (from_counter, root_or_empty(from_root)) == (seen_counter, seen_root):
            if from_head_nonce != seen_nonce:
                raise DataError(
                    "WARD: the attested transition did not consume the WM head nonce this device holds"
                )
        elif (to_counter, root_or_empty(to_root)) == (seen_counter, seen_root):
            if to_head_nonce != seen_nonce:
                raise DataError(
                    "WARD: the WM head nonce changed without the head moving"
                )

    # The WM vouched for it, so record it for the next authorisation this session mints.
    sync_round.set_wm_head(to_counter, root_or_empty(to_root), to_head_nonce)

    # NO TIME CHECK. The attestation still carries a timestamp and it is still covered by the
    # signature, but nothing compares it: anti-replay is the counter's job, a malicious WM simply
    # lies about the clock, and an honest one whose clock regressed without its counter regressing
    # was never an attack. Storing a time to compare against bought nothing, so the device stops
    # storing one -- see `storage.ward`. The field stays on the wire because removing it from the
    # preimage would be a version bump for no gain today.
    return from_counter, root_or_empty(from_root), to_counter, root_or_empty(to_root)


def require_attested_round(what: str) -> "tuple[int, bytes, int, bytes]":
    """The transition this round attested, or refuse.

    An adoption route may only run against a round that reached ATTESTED: the nonce alone proves
    nothing, and a verified signature that was never bound to a tree adopts nothing either.
    """
    from trezor.wire import DataError

    from . import round as sync_round

    attested = sync_round.get_attested()
    if attested is None:
        raise DataError("no attested sync round to " + what)
    return attested


async def verify_inbound_link(
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
    supplied: "bytes | None",
    subject: str = "attested head",
) -> bool:
    """Require that a device of this wallet authorised the attested step. Returns whether it
    reverted.

    THE HOST SUPPLIES ONLY 32 BYTES. All four operands come from the WM's attestation; the host
    contributes the `auth_commit` and nothing else. It used to name the predecessor as well, and
    could choose among any links it held ending at the attested head -- two can coexist, since a
    write and a revert may land on the same root at the same counter. That choice decided which
    transition `offline_store.reconcile_pending` credited and whether the revert warning fired, so
    removing it removes a way for a host to mis-settle a queued change without forging anything.

    WHAT THIS PROVES, AND WHAT IT DOES NOT. The WM signs that this step is current; only a holder
    of K_auth can mint the MAC over it, so together they say the wallet really took it. They do
    NOT say the predecessor descends from THIS device's head -- a WM colluding with a host can
    attest a step off the authoritative line, and only `verify_chain`'s walk back to a state this
    device already holds rules that out. That is why reconcile remains the weaker route.

    EITHER TAG IS ACCEPTED, and which it was is RETURNED rather than swallowed. A demotion is as
    real a transition as a write, and a device catching up across one must be able to say so.

    GENESIS HAS NO LINK. Counter 0 attests itself, no step produced it, and `auth_commit` must
    therefore be absent -- accepting one would mean accepting an authorisation for a transition
    that cannot exist.
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT, root_or_empty
    from .cas import TAG_REVERT, verify_auth_commit
    from .keys import derive_k_auth, derive_ward_id

    if to_counter == 0:
        if supplied is not None:
            raise DataError("WARD: counter 0 has no transition into it")
        if root_or_empty(to_root) != EMPTY_ROOT:
            raise DataError("WARD: counter 0 must be the empty tree")
        return False

    if supplied is None:
        raise DataError("WARD: the link into the " + subject + " is required")

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    if verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, supplied
    ):
        return False
    if verify_auth_commit(
        k_auth,
        ward_id,
        from_counter,
        from_root,
        to_counter,
        to_root,
        supplied,
        TAG_REVERT,
    ):
        return True
    raise DataError("WARD: the link into the " + subject + " is not authorised")


async def adopt(
    counter: int,
    root: bytes | None,
    landed_commits: "list | None" = None,
) -> None:
    """Take the head: settle queued writes, persist it, latch online, close the round.

    THE ORDER IS THE CONTRACT, and each step's reason for being where it is:

      SETTLE FIRST. A claim names the transition it was filed for, so once the stored head is at
      or past that transition the walk that would have proved it is behind every future sync's
      baseline and no later adoption can decide it. Crash before settling and the next sync
      crosses the transition again; crash after and the claim is already resolved. The reverse
      order has no safe crash point.

      THEN PERSIST, AND CHECK THAT IT PERSISTED. `storage.ward` refuses a ninth wallet rather than
      evicting one of the eight it protects, so a full store means the verified head was NOT kept.
      Latching online after that would leave the session verifying against a root that does not
      exist, and `common.verify_leaf_against_root` reads an absent root at counter 0 as "nothing
      was ever written" and stops checking proofs at all.

      THEN LATCH. Reads may go to the host once a WM attestation has been bound to a tree the
      device actually holds AND that attestation answers a nonce from this round. Every caller
      now arrives with both -- see below.

      THEN CLOSE THE ROUND, so one attestation can never be replayed into a second adoption.

    THERE USED TO BE A `current=False` MODE, for a walk anchored on an ARCHIVED attestation: it
    adopted and settled without latching, on the reasoning that descent needs only a head the WM
    genuinely held while currency needs a nonce from this round. The distinction was sound and the
    mode still had to go, because it PERSISTED THE COUNTER -- the `set_root` above runs before the
    latch decision -- which let a host undo a user-confirmed `WardRecoverCounter` by replaying the
    attestation it had kept for the old head. `verify_chain` no longer offers that anchor; see
    `verify_chain._anchor`. Every adoption is now nonce-bound, so there is no second mode to get
    wrong.

    `landed_commits`, when given, is every transition the caller proved it crossed; a claim landed
    exactly when its own authorisation is among them. Without it, settlement asks whether the head
    being adopted is the one that claim's authorisation names -- see
    `offline_store.reconcile_pending`.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .offline_store import reconcile_pending
    from .root import set_root

    # BEFORE `set_root`, and that ordering is now load-bearing twice over: settling has always had
    # to precede persistence (above), and the counter-path check reads the head this adoption is
    # about to replace -- the FROM state a claim's authorisation was minted over.
    await reconcile_pending(counter, root, landed_commits=landed_commits)

    if not await set_root(root, counter):
        raise DataError(
            "WARD: no root slot for this wallet; eight already hold one, so this one can only be used offline"
        )

    sync_round.mark_online()
    sync_round.clear()
