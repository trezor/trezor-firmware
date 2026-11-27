from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardRollForward, WardRollForwardAck

# A link with its WM record is ~250 bytes; the host pages well inside the 8704-byte buffer.
_MAX_LINKS = const(16)


async def roll_forward(msg: WardRollForward) -> WardRollForwardAck:
    """Sign again, for this session, transitions the WM accepted before its register went back.

    A wm_sig is bound to the session nonce of the sync it was minted in, and a restore ends every
    session, so the signatures a host kept are refused by a restored WM. This re-binds the WM's own
    accepted history instead. For each link, oldest first:

    - it starts where the previous one ended, the first at the WM head this round attests;
    - its auth_commit verifies under K_auth: a device of this wallet made this step;
    - its WM record verifies: the WM accepted exactly this step before;
    - where it reaches or crosses this device's stored counter, it agrees with the stored head --
      this device re-authorises only history it is on, never a branch it would refuse.

    Then it is signed under this round's nonce with its original tag (a revert stays a revert).

    ONLY AFTER DETECTION, ONLY WITH APPROVAL. The round's WardIngestAttestation must have found the
    WM below this device's head (`round.roll_forward`). The first page is checked, then the user
    approves; later pages of the same round need no new approval but must start where the previous
    page ended. On the `final` page the device shows the head it restored and the time of the WM's
    record of its last change -- when the WM last vouched for that step, as far as the host's
    records go -- so the user can tell how recent the restored history is. Nothing is adopted
    here; the host submits the signatures as ordinary advances and syncs.
    """
    from trezor.messages import WardRollForwardAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_attested
    from .attest import NONCE_LENGTH, root_or_empty, same_root, verify_attestation
    from .transition import TAG_WM_HEAD, TAG_WM_REVERT, link_of, verify_chain_step, wm_sig
    from .common import change_no, count_changes, has_wm, manager_date, require_initialized
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()
    if not has_wm():
        raise DataError("WARD: this firmware has no WARD Manager to roll forward")
    if not msg.links:
        raise DataError("WARD: no transitions to roll forward")
    if len(msg.links) > _MAX_LINKS:
        raise DataError("WARD: too many transitions in one roll-forward")

    # ONLY IN A ROUND THAT DETECTED A RESTORED WM, and continuing from where it stands.
    state = sync_round.roll_forward()
    ctx = sync_round.get()
    if state is None or ctx is None or state[1] != ctx[1]:
        raise DataError("WARD: no restored WM detected in this round; sync first")
    approved = state[0] == sync_round.ROLL_FORWARD_APPROVED

    # The WM's head, attested against this round: where the replay starts, and the session.
    _fc, _fr, counter, root = await verify_attested(msg)
    if counter != state[2] or not same_root(root, state[3]):
        raise DataError("WARD: the WM head is not where the roll-forward stands")
    session_nonce = sync_round.require_session_nonce()
    wm_counter = counter

    k_auth = await derive_k_auth()
    k_sig = await derive_k_sig()
    ward_id = await derive_ward_id()
    stored_counter = await get_counter()
    stored_root = await get_root()

    sigs = []
    last_timestamp = 0
    for link in msg.links:
        step = link_of(link)
        fc, fr, tc, tr, _mac = step
        to_counter, to_root, reverted = verify_chain_step(
            k_auth, ward_id, counter, root, step
        )
        receipt = link.acceptance
        if (
            receipt is None
            or receipt.nonce is None
            or len(receipt.nonce) != NONCE_LENGTH
            or receipt.timestamp is None
            or receipt.wm_signature is None
            or not verify_attestation(
                ward_id,
                receipt.nonce,
                fc,
                fr,
                tc,
                tr,
                receipt.timestamp,
                receipt.wm_signature,
            )
        ):
            raise DataError("WARD: no WM record that this transition was accepted")
        if (
            fc < stored_counter < tc
            or (fc == stored_counter and not same_root(fr, stored_root))
            or (tc == stored_counter and not same_root(tr, stored_root))
        ):
            raise DataError("WARD: the transitions are not on this device's history")
        sigs.append(
            wm_sig(
                k_sig,
                ward_id,
                fc,
                fr,
                tc,
                tr,
                TAG_WM_REVERT if reverted else TAG_WM_HEAD,
                session_nonce,
            )
        )
        counter, root = to_counter, to_root
        last_timestamp = receipt.timestamp

    if not approved:
        await confirm_properties(
            "ward_roll_forward",
            "Restore WARD history",
            [
                ("WARD Manager", change_no(wm_counter), False),
                ("This device", change_no(stored_counter), False),
                ("Sign again", count_changes(counter - wm_counter), False),
                (
                    "Note",
                    "The WARD Manager was restored to an earlier state. Changes it accepted "
                    "before will be signed again for this session.",
                    False,
                ),
            ],
        )

    if msg.final:
        sync_round.clear_roll_forward()
        await confirm_properties(
            "ward_roll_forward_done",
            "WARD history restored",
            [
                ("Restored to", change_no(counter), False),
                ("Last confirmed", manager_date(last_timestamp), False),
            ],
        )
    else:
        sync_round.set_roll_forward(
            sync_round.ROLL_FORWARD_APPROVED, state[1], counter, root_or_empty(root)
        )

    return WardRollForwardAck(wm_sigs=sigs, last_timestamp=last_timestamp)
