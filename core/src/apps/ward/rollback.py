from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRollback, WardRollbackAck


async def rollback(msg: WardRollback) -> WardRollbackAck:
    """Demote the head to an earlier state of this wallet, with the user's consent.

    This is the escape from a wallet no host can serve, and it deliberately needs NO
    attestation -- requiring one would make the escape unavailable in the situation it
    exists for.

    WHY, PRECISELY. The freshness authority and the data store are DIFFERENT SYSTEMS. The WM
    vouches for (counter, mac); the leaves live in an eventually-consistent store. A host
    writes, the device commits, the WM CONFIRMS -- and the row still never reaches the relay.
    A second host syncs, is missing that row, and cannot reconstruct the tree at the current
    root. Device and WM agree perfectly; that host can serve no proof at all, and the wallet
    is unusable there. Reverting to the last root that host CAN reconstruct is the only way
    back. Note the device is not ahead of the WM in that story: an earlier version of this
    file claimed that was the reason, and it is only one of them.

    WHY IT IS NOT ONE STEP. Undoing step N means presenting the COMMIT for (N-1 -> N), and in
    the story above that link is part of what never synced. The missing range therefore
    cannot be walked one step at a time -- the only reachable move is a single jump to the
    last state whose link the host actually has. Multi-step is not a convenience here;
    stepping is impossible.

    WHAT IS STILL PROVEN. The host presents the link INTO the target: (from_counter,
    from_root) -> (to_counter, to_root) with its COMMIT authorisation, which only a device of
    this wallet could have produced. That establishes the target is a state this wallet
    genuinely committed, at a counter that is itself inside the MAC preimage -- so the count
    of what is being discarded is authenticated rather than asserted by the host. That
    matters more than it sounds: it is what lets the screen state a number the user can act
    on.

    WHAT IS NOT PROVEN, AND MUST NOT BE IMPLIED. The target is no longer required to be the
    immediate predecessor of the current head, so:

      a host may present ANY historical link, including one from an orphaned fork;
      rollbacks can now CHAIN, which they could not before -- a rollback's own transition is
        authorised as a REVERT and this check demands a COMMIT, so the presented link is
        always a historical COMMIT and nothing stops a second demotion.

    The adversary this guards against is a malicious host reverting the wallet, and it cannot
    be told apart from an honest one: the device cannot verify a claim of missing data,
    because absence is unprovable. So what the design buys is not prevention. It converts an
    unbounded SILENT rewind into one where the user is told, from authenticated values,
    exactly how much is at stake -- and the count discriminates in practice, since an honest
    recovery discards the few writes that failed to propagate while damaging malice must go
    deep and ask the user to approve an obviously large number. A shallow malicious revert
    stays cheap and indistinguishable. Bounded loss, not prevented loss.

    ON THE AGE THE DESIGN ASKED FOR: it cannot be shown, and the discarded COUNT is what
    replaces it. The device has no clock, so "now" must come from the host or the WM. A
    host-supplied now is worthless against precisely this attack -- the attacker controls it
    and needs only to make an old change look FRESH, so a number the adversary picks cannot
    bound the adversary. The WM's time arrives through `ingest`, which refuses an attestation
    below the stored counter, i.e. exactly the state this exists for.

    THE WM NEEDS NO SPECIAL HANDLING and no operator does anything. The revert lands at
    counter + 1 carrying the older root, which the WM accepts as an ordinary forward advance,
    verifying the auth_sig below under ward_id exactly as it would for a write. Other devices
    then sync to the reverted state through the normal round. Not to be confused with
    `WardRecoverCounter`, which is the only path accepting a LOWER counter and exists for the
    WM's own register or clock regressing -- a different failure, where the WM's state is the
    broken thing rather than a host's.
    """
    from trezor.messages import WardRollbackAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .cas import TAG_REVERT, auth_commit, sig_commit, verify_auth_commit
    from .common import WARNING_UNVERIFIED, require_initialized
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id
    from .root import get_attested_counter, get_counter, get_root, set_root

    require_initialized()

    counter = await get_counter()
    head = await get_root()
    if counter < 1:
        raise DataError("cannot roll back the first state")

    to_root = msg.to_root or None
    from_root = msg.from_root or None
    supplied = msg.auth_commit
    to_counter = msg.to_counter
    from_counter = msg.from_counter
    if supplied is None or to_counter is None or from_counter is None:
        raise DataError("the link into the target is required")

    # Shape first, so a malformed link cannot reach the MAC check and be judged on its
    # authenticity alone. A link is one transition, and the target has to be in the past.
    if to_counter != from_counter + 1:
        raise DataError("link must advance the counter by exactly one")
    if to_counter >= counter:
        raise DataError("target must precede the current head")

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # The check that does the work: this authorisation must describe the transition that
    # PRODUCED the target state. Only a device of this wallet can mint it, so the target
    # cannot be invented -- and because to_counter is inside the preimage, the discarded
    # count derived from it below is authenticated too.
    if not verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, supplied
    ):
        raise DataError("auth_commit does not describe the target state")

    # Both numbers come from authenticated values: `counter` is the device's own, and
    # `to_counter` is covered by the MAC just verified. The attested counter is kept
    # separately from the head counter precisely so this second number can be stated -- the
    # head is advanced by writes too, so it cannot say what the WM confirmed.
    discarded = counter - to_counter
    confirmed = await get_attested_counter() - to_counter
    if confirmed < 0:
        confirmed = 0

    props = [
        (
            "Discarding",
            "%d change%s" % (discarded, "" if discarded == 1 else "s"),
            False,
        ),
    ]
    if confirmed:
        # The part another device may already hold, and therefore the destructive part.
        props.append(("Already synced", "%d of them" % confirmed, False))
    props.append(("Restoring", "change #%d" % to_counter, False))
    props.append(("Warning", "Discarded changes cannot be recovered.", False))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_rollback", "Revert changes", props, hold=True)

    # Forward, even though the head goes back. Reusing a counter would let the writes being
    # undone replay afterwards, since their authorisations name those counters -- and it is
    # also what lets the WM accept this as an ordinary advance.
    new_counter = counter + 1
    await set_root(to_root, new_counter)

    return WardRollbackAck(
        counter=new_counter,
        new_root=to_root,
        auth_commit=auth_commit(
            k_auth, ward_id, counter, head, new_counter, to_root, TAG_REVERT
        ),
        auth_sig=sig_commit(
            await derive_k_sig(),
            ward_id,
            counter,
            head,
            new_counter,
            to_root,
            TAG_REVERT,
        ),
    )
