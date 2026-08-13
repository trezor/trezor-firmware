from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDIngestAttestation, WARDIngestAttestationAck


async def ingest(msg: WARDIngestAttestation) -> WARDIngestAttestationAck:
    """Verify the WM's attestation of the current (counter, mac) for this round.

    Adopts nothing: the root has not been seen yet. This step establishes only that some
    authority the device trusts says a particular (counter, mac) is current, and that the
    statement was made in response to THIS round's nonce.
    """
    from trezor.messages import WARDIngestAttestationAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import verify_attestation
    from .common import require_initialized
    from .keys import derive_ward_id
    from .root import get_counter

    require_initialized()

    ctx = sync_round.get()
    if ctx is None:
        raise DataError("no sync round in progress")
    _state, nonce, _c, _m = ctx

    counter = msg.counter
    mac = msg.mac
    signature = msg.wm_signature
    if counter is None or mac is None or signature is None:
        raise DataError("counter, mac and wm_signature are required")

    if not verify_attestation(await derive_ward_id(), nonce, counter, mac, signature):
        raise DataError("WM attestation verification failed")

    # Anti-rollback. The attested counter may not precede the floor this wallet has
    # already accepted; equality is fine, since re-reading the same state is a no-op.
    # A malicious WM cannot forge a mac, so its entire remaining freedom is to replay a
    # state this wallet genuinely reached -- and this is what bounds which ones.
    if counter < await get_counter():
        raise DataError("attested counter is older than the stored counter")

    sync_round.set_attested(counter, mac)
    return WARDIngestAttestationAck(counter=counter)
