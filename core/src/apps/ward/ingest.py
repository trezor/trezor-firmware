from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardIngestAttestation, WardIngestAttestationAck


async def ingest(msg: WardIngestAttestation) -> WardIngestAttestationAck:
    """Verify the WM's attestation of the transition that reached the current head.

    Establishes freshness only and adopts nothing: the WM signs roots in the clear, so only a
    link or chain folded later (`reconcile`, `verify_chain`) ties the head to this wallet.

    A HEAD BELOW THIS DEVICE'S is not adopted, and not refused either: the WM's register went
    back (a restored backup, a failover onto a stale replica). The round is NOT attested, so
    nothing can be adopted from it; the ack says `wm_behind`, and the round may continue with
    `WardRollForward`, which re-signs the history the WM accepted before, with the user's approval.
    """
    from trezor.messages import WardIngestAttestationAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_attested
    from .common import require_initialized
    from .root import get_counter

    require_initialized()

    from_counter, from_root, counter, root = await verify_attested(msg)

    # Anti-rollback floor. The one exemption is the exact demotion the user approved, from the
    # head they approved it at (`round.demotion_matches`).
    stored = await get_counter()
    if counter < stored and not sync_round.demotion_matches(
        stored, from_counter, from_root, counter, root
    ):
        ctx = sync_round.get()
        if ctx is None:
            raise DataError("no sync round in progress")
        sync_round.set_roll_forward(sync_round.ROLL_FORWARD_DETECTED, ctx[1], counter, root)
        return WardIngestAttestationAck(counter=counter, wm_behind=True, stored_counter=stored)

    sync_round.set_attested(from_counter, from_root, counter, root)
    return WardIngestAttestationAck(counter=counter)
