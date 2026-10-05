from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardIngestAttestation, WardIngestAttestationAck


async def ingest(msg: WardIngestAttestation) -> WardIngestAttestationAck:
    """Verify the WM's attestation of the transition that reached the current head.

    Establishes freshness only and adopts nothing: the WM signs roots in the clear, so only a
    link or chain folded later (`reconcile`, `verify_chain`) ties the head to this wallet.
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
        raise DataError("attested counter is older than the stored counter")

    sync_round.set_attested(from_counter, from_root, counter, root)
    return WardIngestAttestationAck(counter=counter)
