"""What every route into a new head has in common: verifying the WM's attestation against the
round, verifying the link into the attested head, and adopting it.

The route-specific proof (reconcile's single link, verify_chain's backward walk) stays with each
handler; `verify_inbound_link` and `adopt` are separate because reconcile checks between them.
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

    Applies no counter rule (callers want opposite ones) and adopts nothing. Returns both roots in
    preimage form. Latches the WM head `(to_counter, to_root, to_head_nonce)` once the signature
    verifies, even if the caller then refuses the attestation.

    Continuity against the latched head (session-scoped): if the attested `from` end is that head,
    the WM must have consumed the nonce latched for it (R1); if the `to` end is that head, the WM
    has not moved and its nonce must not have changed (R2) -- that catches a register restore.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_or_empty, verify_attestation
    from .cas import MAX_BATCH, NO_HEAD_NONCE
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

    # A live head never carries the enrolment constant: a head left at it would make the first
    # write after genesis replayable into any future re-enrolment.
    if NO_HEAD_NONCE in (from_head_nonce, to_head_nonce):
        raise DataError("WARD: the attested WM head carries the enrolment nonce")
    for r in (from_root, to_root):
        if r is not None and len(r) != 32:
            raise DataError("attested roots must be 32 bytes")

    # A step advances by 1..MAX_BATCH and rotates the nonce; genesis attests itself.
    if to_counter == 0:
        if from_counter != 0 or root_or_empty(from_root) != root_or_empty(to_root):
            raise DataError("WARD: counter 0 must attest itself")
        if from_head_nonce != to_head_nonce:
            raise DataError("WARD: counter 0 consumed no head nonce")
    elif not 1 <= to_counter - from_counter <= MAX_BATCH:
        raise DataError("WARD: an attested transition advances the counter by 1 to MAX_BATCH")
    elif from_head_nonce == to_head_nonce:
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

    # Continuity (R1, R2), after the signature so the compared values are WM-vouched.
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

    sync_round.set_wm_head(to_counter, root_or_empty(to_root), to_head_nonce)
    # The timestamp is signed but deliberately not checked: anti-replay is the counter's job.
    return from_counter, root_or_empty(from_root), to_counter, root_or_empty(to_root)


def require_attested_round(what: str) -> "tuple[int, bytes, int, bytes]":
    """The transition this round attested, or refuse: only an ATTESTED round may be adopted."""
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
    """Require that a device of this wallet authorised the attested step; return whether it was
    a REVERT. The host supplies only the MAC -- every operand comes from the attestation. Proves
    the wallet took this step, not that it descends from this device's head (`verify_chain` does).
    Counter 0 has no link, so a supplied one is refused.
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

    The order is the contract: settle claims before the head moves past them; refuse if the root
    was not persisted (a missing root would read as "nothing written" and disable proof checks);
    only then latch online; finally close the round so the attestation cannot be replayed.
    `landed_commits` lists the transitions the caller proved it crossed -- see
    `offline_store.reconcile_pending`.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .offline_store import reconcile_pending
    from .root import set_root

    # Before `set_root`: settlement reads the head being replaced.
    await reconcile_pending(counter, root, landed_commits=landed_commits)

    if not await set_root(root, counter):
        raise DataError(
            "WARD: no root slot for this wallet; eight already hold one, so this one can only be used offline"
        )

    sync_round.mark_online()

    # Any adoption spends a pending demotion consent: it was given for a descent from the old head.
    sync_round.clear_demotion()
    sync_round.clear()
