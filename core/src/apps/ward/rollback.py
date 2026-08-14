from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDRollback, WARDRollbackAck


async def rollback(msg: WARDRollback) -> WARDRollbackAck:
    """Demote the head by exactly one step, with the user's consent.

    This is the escape from a stuck wallet. A device whose write never reached the WM is
    ahead of it, so every sync is refused as a rollback and nothing can move; undoing that
    write is the only way forward. It deliberately needs NO attestation -- requiring one
    would make the escape unavailable in exactly the situation it exists for.

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

    FIXME(ward): the design puts the AGE of the discarded change on this screen and calls
    it the actionable signal -- a legitimate rollback discards something minutes old, while
    "created 3 months ago" means a host is rewinding under cover of a fabricated deadlock.
    We have no timestamps, so the screen names the change but cannot date it. Add the age
    with the timestamp work; until then this prompt is weaker than the design intends.
    """
    from trezor.messages import WARDRollbackAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .cas import TAG_REVERT, auth_commit, verify_auth_commit
    from .common import WARNING_UNVERIFIED, require_initialized
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root, set_root

    require_initialized()

    counter = await get_counter()
    head = await get_root()
    if counter < 1:
        raise DataError("cannot roll back the first state")

    to_root = msg.to_root or None
    supplied = msg.auth_commit
    if supplied is None:
        raise DataError("auth_commit is required")

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

    return WARDRollbackAck(
        counter=new_counter,
        new_root=to_root,
        auth_commit=auth_commit(
            k_auth, ward_id, counter, head, new_counter, to_root, TAG_REVERT
        ),
    )
