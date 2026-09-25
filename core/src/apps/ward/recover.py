from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRecoverCounter, WardRecoverCounterAck


async def recover(msg: WardRecoverCounter) -> WardRecoverCounterAck:
    """Demote onto a state the host can still serve, when the WM's register went backwards.

    NAMED FOR ITS MODULE, not for what it does: `find_registered_handler` derives the function
    name from the last component of the path it is registered under, so this must be `recover` in
    `apps.ward.recover`. A mismatch fails at `getattr`, before any check in the body runs, so
    every caller sees the same opaque failure whatever it asked for.

    A RECOVERY IS A ROLLBACK, and is now built as one. Monotonicity is what stops a replay, and
    when the WM's register is lost it becomes a denial of service against the owner instead:
    every device with a stored counter locks out and nothing syncs again. The way back is the
    same operation `rollback` performs -- a REVERT transition, counter forward, carrying a root
    from further back -- and the only thing that differs is which head it is built FROM.

    FROM THE WM'S HEAD, NOT THIS DEVICE'S. That is the whole distinction. Normally they are the
    same, because a device only ever adopts what the WM attested; after a register loss they are
    not, and the WM's is the one a transition must extend if the WM is to accept it at all. So
    this mints

        (wm_counter, wm_root) -> (wm_counter + 1, recovered_root)

    under TAG_REVERT, with `auth_commit` for the other devices and `wm_sig` for the WM.

    THE COUNTER GOES FORWARD, which is what makes it safe to re-use a number the wallet has
    already been past. It also breaks the replay that lowering the counter used to open: an
    authorisation binds its exact `(from_counter, from_root)` predecessor, so once the head is
    `(11, recovered_root)` the old links out of `(11, R11)` no longer apply and the history above
    cannot be re-driven. That holds unless `recovered_root` happens to equal the root that
    genuinely held that counter -- roots are content-addressed and may repeat -- which is a
    narrower residue than the wholesale re-opening a backward jump used to leave.

    WHAT `recovered_root` IS, AND WHAT IT IS NOT. It is a root the HOST can reconstruct from the
    data it actually holds -- Suite proposes it, having rebuilt the trie from its own rows -- and
    the user approves it on the screen below. It is NOT required to have been a head: a host that
    lost rows reconstructs a tree the wallet may never have had, and reverting to something
    serviceable is the entire point of the escape hatch. `WardRollback` demands an archived
    attestation for exactly this reason and can afford to, because it runs when the WM is healthy
    and the target really was current. Here the WM's register is the thing that is gone, so the
    user's approval is the authority, and the screen has to say so rather than imply a proof that
    does not exist.

    NOTHING IS ADOPTED HERE. The device hands back the transition and the head moves only when the
    WM has confirmed it, which is the invariant every write obeys. What IS recorded is the
    user's consent -- `round.authorise_demotion` -- because the attestation that comes back names
    a counter below this device's floor, and `ingest` and `reconcile` would both otherwise be
    right to refuse it.

    WHAT CANNOT BE CHECKED IS INTENT. Nothing distinguishes a genuine operator recovery from an
    attacker walking a user through one: both present the same authentic material, and the
    difference lives entirely in whether the user means it. That makes this the strongest
    social-engineering target in the protocol, so the screen names both counters, says how far
    back the state is, and holds.
    """
    from trezor.messages import WardRecoverCounterAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_round_attestation
    from .cas import TAG_REVERT, TAG_WM_REVERT, auth_commit, wm_sig
    from .common import WARNING_UNVERIFIED, require_initialized
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id
    from .root import get_counter

    require_initialized()

    # THE WM'S OWN HEAD, attested against this round's nonce. It is the predecessor the demotion
    # extends and the value the WM will compare-and-swap on, so it has to be its current one and
    # not something the host names.
    _wm_from_counter, _wm_from_root, wm_counter, wm_root = await verify_round_attestation(
        msg.from_counter,
        msg.from_root or None,
        msg.to_counter,
        msg.to_root or None,
        msg.timestamp or 0,
        msg.wm_signature,
    )

    stored_counter = await get_counter()

    # Refuse to be used for anything but its purpose. A WM that is not BEHIND this device has not
    # lost anything, and a demotion from a healthy WM is `WardRollback` -- which requires proof
    # the target was ever the head, and should not be reachable through a screen that does not.
    if wm_counter >= stored_counter:
        raise DataError("the WM is not behind this device; use WardRollback")

    recovered_root = msg.recovered_root or None
    if recovered_root is not None and len(recovered_root) != 32:
        raise DataError("recovered_root must be 32 bytes")

    new_counter = wm_counter + 1

    await confirm_properties(
        "ward_recover_counter",
        "Reset sync counter",
        [
            ("Currently at", "change #%d" % stored_counter, False),
            ("Resetting to", "change #%d" % new_counter, False),
            ("Going back", "%d changes" % (stored_counter - new_counter), False),
            (
                "Warning",
                "Changes after #%d may be lost. Only continue if you are recovering "
                "the sync service." % new_counter,
                False,
            ),
            # SAYS WHAT WAS NOT PROVEN, which is the honest counterpart to the line
            # `WardRollback` shows. There the WM confirmed the target; here the WM's record is
            # the thing that was lost, so the state being restored is one the host says it can
            # serve and nothing more.
            (
                "Target",
                "Proposed by the host. Not confirmed by the WARD Manager.",
                False,
            ),
            WARNING_UNVERIFIED,
        ],
        hold=True,
    )

    ward_id = await derive_ward_id()

    # RECORDED ONLY AFTER THE HOLD. The attestation that brings this head back names a counter
    # below this device's floor, and nothing else would let it through.
    sync_round.authorise_demotion(new_counter)

    return WardRecoverCounterAck(
        counter=new_counter,
        new_root=recovered_root,
        auth_commit=auth_commit(
            await derive_k_auth(),
            ward_id,
            wm_counter,
            wm_root,
            new_counter,
            recovered_root,
            TAG_REVERT,
        ),
        wm_sig=wm_sig(
            await derive_k_sig(),
            ward_id,
            wm_counter,
            wm_root,
            new_counter,
            recovered_root,
            TAG_WM_REVERT,
        ),
    )
