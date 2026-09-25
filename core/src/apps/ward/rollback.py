from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRollback, WardRollbackAck


async def rollback(msg: WardRollback) -> WardRollbackAck:
    """Demote the head to a state the host can still serve, with the user's consent.

    ONE OPERATION FOR TWO FAILURES, which used to be two handlers and were never really
    different. `WardRecoverCounter` existed for a WM whose register or clock regressed; this
    existed for a host that could not reconstruct the tree at the current root. Both mint the
    same thing -- a REVERT from a head to head+1, carrying a root from further back -- and both
    rest on the user, so keeping them apart only invited the two to drift.

        (wm_counter, wm_root) -> (wm_counter + 1, recovered_root)   under TAG_REVERT

    BUILT FROM THE WM'S HEAD, NOT THIS DEVICE'S. That is what collapses the two cases. A device
    only ever adopts what the WM attested, so normally the two heads are the SAME and this is an
    ordinary rollback landing at `counter + 1`. When the WM's register has regressed they differ,
    and building from the WM's is the only thing it will compare-and-swap against -- which is
    exactly what recovery needed. The device does not have to know which failure it is in.

    WHY A HOST NEEDS THIS AT ALL. The freshness authority and the data store are DIFFERENT
    SYSTEMS. The WM vouches for `(counter, root)`; the leaves live in an eventually-consistent
    store. A host writes, the device commits, the WM confirms -- and the row still never reaches
    the relay. A second host syncs, is missing that row, and cannot reconstruct the tree at the
    current root. Device and WM agree perfectly; that host can serve no proof at all, and the
    wallet is unusable there. Reverting to the last root it CAN reconstruct is the only way back.

    THE COUNTER GOES FORWARD even though the head goes back, and that is what makes re-using a
    number the wallet has already passed safe: the authorisations being stepped over keep naming
    counters the head has moved past, so they cannot be re-presented as current. It is also what
    lets the WM accept this as an ordinary advance, needing no special handling and no operator.

    NO PROOF THAT THE TARGET WAS EVER THE HEAD, and that requirement is withdrawn rather than
    relaxed. It briefly demanded the archived attestation the WM issued when the target was
    current, so that an abandoned branch could not be restored. It asks for something this
    situation cannot supply: the state a host can rebuild is whatever its own rows hash to, and a
    host missing rows is exactly one whose reconstructible root the WM may never have attested.
    Demanding proof of headship made the escape unavailable in the case it exists for -- the same
    objection that had already defeated requiring a LIVE attestation, arriving one step later.

    SO THE USER IS THE AUTHORITY, and the screen says so rather than implying a proof nobody is
    making. What the device still refuses is a malformed step: the WM's attestation is checked
    against this round's nonce like any other, so the head being extended is the WM's real one.

    WHAT CANNOT BE CHECKED IS INTENT. Nothing distinguishes a genuine recovery from an attacker
    walking a user through one -- both present the same authentic material, and the difference
    lives entirely in whether the user means it. That makes this the strongest social-engineering
    target in the protocol, so the screen names where the wallet is, where it is going, how far
    back that is, and what was not proven, and holds. Bounded loss, not prevented loss.

    NOTHING IS ADOPTED HERE. The ack carries the transition and the head moves only once the WM
    has confirmed it, which is the invariant every write obeys. What IS recorded, when the new
    counter does not advance this device, is the user's consent for that exact counter --
    otherwise `ingest` and `reconcile` would both be right to refuse the attestation that brings
    it back.
    """
    from trezor.messages import WardRollbackAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_round_attestation
    from .attest import root_or_empty
    from .cas import TAG_REVERT, TAG_WM_REVERT, auth_commit, wm_sig
    from .common import WARNING_UNVERIFIED, require_initialized
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id
    from .root import get_counter

    require_initialized()

    # THE WM'S OWN HEAD, attested against this round's nonce. It is the predecessor the demotion
    # extends and the pair the WM will compare-and-swap on, so it has to be the WM's current head
    # and not a state the host names.
    _fc, _fr, wm_counter, wm_root = await verify_round_attestation(
        msg.from_counter,
        msg.from_root or None,
        msg.from_head_nonce,
        msg.to_counter,
        msg.to_root or None,
        msg.to_head_nonce,
        msg.timestamp or 0,
        msg.wm_signature,
    )

    recovered_root = msg.recovered_root or None
    if recovered_root is not None and len(recovered_root) != 32:
        raise DataError("recovered_root must be 32 bytes")

    stored_counter = await get_counter()
    new_counter = wm_counter + 1

    props = [
        ("Currently at", "change #%d" % stored_counter, False),
        ("Restoring at", "change #%d" % new_counter, False),
    ]
    # HOW MUCH IS AT STAKE, from authenticated numbers: the stored counter is the device's own
    # and the new one comes from the WM's verified attestation. A deep demotion has to look
    # different from a shallow one, because that is the only thing separating an honest recovery
    # -- which discards the few writes that failed to propagate -- from damaging malice, which
    # must go deep and ask the user to approve an obviously large number.
    if new_counter <= stored_counter:
        discarded = stored_counter - new_counter
        props.append(
            (
                "Discarding",
                "%d change%s" % (discarded, "" if discarded == 1 else "s"),
                False,
            )
        )
    props.append(
        ("Warning", "Discarded changes cannot be recovered.", False)
    )
    # SAYS WHAT WAS NOT PROVEN. The target is the host's proposal -- a tree it says it can
    # rebuild -- and whether it was ever the authoritative head is not established. This line is
    # the only place the user learns that, so it must not read as a guarantee.
    props.append(
        ("Target", "Proposed by the host. Not confirmed by the WARD Manager.", False)
    )
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_rollback", "Revert changes", props, hold=True)

    # RECORDED ONLY AFTER THE HOLD, and only when it is needed: a demotion that still advances
    # this device's counter needs no exemption, and granting one would widen the rule for nothing.
    if new_counter <= stored_counter:
        # THE EXACT TRANSITION, not just the counter it lands on. The attestation that brings
        # this back must be THIS demotion and not merely one at the same number -- a different
        # root there is a different state than the one the user was shown.
        sync_round.authorise_demotion(
            stored_counter, wm_counter, wm_root, new_counter, root_or_empty(recovered_root)
        )

    ward_id = await derive_ward_id()

    # BOTH authorisations, because the demotion has two audiences. `auth_commit` under TAG_REVERT
    # is what another device of this wallet folds when it walks the history; `wm_sig` under
    # TAG_WM_REVERT is what the WM checks before moving its head.
    #
    # The WM one needs its own tag for a reason the operands cannot supply: a revert advances the
    # head exactly like a write -- forward one counter, carrying an OLDER root -- so without the
    # tag the WM cannot tell a demotion from an ordinary advance and cannot apply policy to one.
    # Both cover the same transition, so the two cannot come to disagree about which moment this
    # demotion re-dates.
    #
    # THE HEAD NONCE IS THE ONE JUST ATTESTED, latched by `verify_round_attestation` a few lines
    # up, and this operation is why it exists. A demotion carries an OLD root forward under a new
    # counter, so it is the one transition that deliberately re-creates a `(counter, root)` pair
    # the wallet may have held before -- and without the nonce, an authorisation minted for the
    # earlier occurrence would be live again at the later one. Quoting the WM's current nonce
    # pins this revert to this moment in the WM's history and no other.
    return WardRollbackAck(
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
            sync_round.require_head_nonce(),
            TAG_WM_REVERT,
        ),
    )
