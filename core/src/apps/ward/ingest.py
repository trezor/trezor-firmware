from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardIngestAttestation, WardIngestAttestationAck


async def ingest(msg: WardIngestAttestation) -> WardIngestAttestationAck:
    """Verify the WM's attestation of the current (counter, mac) for this round.

    Adopts nothing: the root has not been seen yet. This step establishes only that some
    authority the device trusts says a particular (counter, mac) is current, and that the
    statement was made in response to THIS round's nonce.
    """
    from trezor.messages import WardIngestAttestationAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_round_attestation
    from .common import require_initialized
    from .root import get_counter

    require_initialized()

    counter, mac = await verify_round_attestation(msg)

    # Anti-rollback, and the reason this rule lives HERE rather than in the shared check:
    # `recover` needs the opposite one. The attested counter may not precede the floor this
    # wallet has already accepted; equality is fine, since re-reading the same state is a no-op.
    # A malicious WM cannot forge a mac, so its entire remaining freedom is to replay a state
    # this wallet genuinely reached -- and this is what bounds which ones.
    if counter < await get_counter():
        raise DataError("attested counter is older than the stored counter")

    sync_round.set_attested(counter, mac)
    return WardIngestAttestationAck(counter=counter)
