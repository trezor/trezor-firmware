from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRollback, WardRollbackAck


async def rollback(msg: WardRollback) -> WardRollbackAck:
    """Demote the head by exactly one step, with the user's consent.

    This is the escape from a stuck wallet, and there are two ways to get stuck. It
    deliberately needs NO attestation -- requiring one would make the escape unavailable in
    exactly the situation it exists for.

    THE DURABLE REASON: the freshness authority and the data store are DIFFERENT SYSTEMS.
    The WM vouches for (counter, mac); the leaves live in an eventually-consistent store
    (an Evolu relay). A confirmation from the first says nothing about durability in the
    second, so a device can commit a head whose backing data was never persisted -- a
    client wrote locally, the relay never received it, that client's database went away.
    The device is then committed to a root NO host can ever produce proofs against, for
    good. Nothing else in the protocol recovers from that.

    THE TRANSIENT REASON: a device whose write never reached the WM is ahead of it, so every
    sync is refused as a rollback. This one disappears if writes ever commit only on WM
    confirmation; the durable reason above does not, because that confirmation is not a
    durability guarantee.

    AND THE PART THAT MAKES THIS DANGEROUS: a host that is merely BEHIND is indistinguishable
    from data that is GONE. Both present as proofs that do not match the trusted root -- see
    `common._verify_against_root`. Rolling back in the first case destroys a legitimate
    change. An eventually-consistent backend makes the first case ORDINARY, which means users
    meet this screen during normal operation and learn to approve it. That is how a
    hold-to-confirm stops being read, and it makes the rewind attack below more practical
    rather than less. The screen alone cannot separate the two cases; only the age can.

    The design's own framing is that the naive version of this -- signing a demotion to a
    root the host names -- is the single most exploitable path in the protocol: a host that
    fakes a stuck state can otherwise rewind the wallet to any point in its history,
    silently. Four constraints close it, and all four are enforced below:

      the host must present the COMMIT authorisation that created the current head, which
        only a device of this wallet could have produced;
      that authorisation must name this device's OWN counter and root, so it is about the
        state actually held rather than some earlier one;
      the demotion target is whatever that authorisation names as its predecessor, never a
        free-form root the host chooses;
      and it moves exactly one step, so rewinding further costs one confirmation each.

    Binding the counter is not redundant with binding the root. Roots repeat whenever
    contents repeat, so an OLD authorisation whose `to_root` happens to equal today's head
    would otherwise demote the wallet to a state from arbitrarily long ago in a single hop,
    with the one-step rule perfectly satisfied.

    ON THE AGE THE DESIGN ASKED FOR, which was previously a FIXME here: it cannot be shown
    the obvious way, and the bound above is what replaces it.

    The design wants the discarded change's age on screen, on the grounds that a legitimate
    rollback discards something minutes old while "created 3 months ago" means a host is
    rewinding under cover of a fabricated deadlock. The device has no clock, so the only
    sources of "now" are the host and the WM. NEITHER WORKS:

      A host-supplied "now" is worthless against precisely this attack. The attacker controls
      it, and the direction they need is to make an old change look FRESH -- claim now is
      about equal to the stored attested time and the age reads as minutes. A number the
      adversary picks cannot bound the adversary.

      The WM's time arrives through `ingest`, which refuses an attestation whose counter is
      below the stored one. That is exactly the state rollback exists for, so the WM's time
      is unavailable in the one situation it would be needed.

    So the screen still names the change without dating it, and the protection is mechanical
    instead: the attested-counter bound above, plus the requirement that the presented
    authorisation be a COMMIT -- which means a rollback cannot be chained, since the
    transition a rollback produces is authorised as a REVERT.
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
    supplied = msg.auth_commit
    if supplied is None:
        raise DataError("auth_commit is required")

    # A change the WM has CONFIRMED is one it demonstrably knows about, so the justification
    # for rolling back -- "my write never reached the WM, and it refuses every sync as a
    # rollback" -- cannot apply to it. Demoting below the attested counter therefore has no
    # legitimate use, and refusing is a mechanical bound where previously only a screen stood
    # between a host and the most recent confirmed write.
    #
    # This needs the attested counter kept SEPARATELY (see `storage.ward`): the head counter
    # is advanced by writes too, so it cannot say what was confirmed. Zero means never
    # synced, which correctly bounds nothing.
    attested = await get_attested_counter()
    if counter - 1 < attested:
        raise DataError(
            "cannot discard a change the sync service has already confirmed"
        )

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # The one check that does all the work: this authorisation must describe the step that
    # produced the state the device is holding RIGHT NOW.
    if not verify_auth_commit(
        k_auth, ward_id, counter - 1, to_root, counter, head, supplied
    ):
        raise DataError("auth_commit does not describe the current head")

    await confirm_properties(
        "ward_rollback",
        "Revert change",
        [
            ("Discarding", "change #%d" % counter, False),
            ("Restoring", "the state before it", False),
            ("Warning", "The discarded change cannot be recovered.", False),
            WARNING_UNVERIFIED,
        ],
        hold=True,
    )

    # Forward, even though the head goes back. Reusing the counter would let the write
    # being undone replay afterwards, since its authorisation names that counter.
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
