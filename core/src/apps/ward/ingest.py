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
    from .attest import EPSILON_SECONDS, verify_attestation
    from .common import require_initialized
    from .keys import derive_ward_id
    from .root import get_counter, get_timestamp

    require_initialized()

    ctx = sync_round.get()
    if ctx is None:
        raise DataError("no sync round in progress")
    _state, nonce, _c, _m, _t = ctx

    counter = msg.counter
    mac = msg.mac
    signature = msg.wm_signature
    timestamp = msg.timestamp or 0
    if counter is None or mac is None or signature is None:
        raise DataError("counter, mac and wm_signature are required")

    if not verify_attestation(
        await derive_ward_id(), nonce, counter, mac, timestamp, signature
    ):
        raise DataError("WM attestation verification failed")

    # Anti-rollback. The attested counter may not precede the floor this wallet has
    # already accepted; equality is fine, since re-reading the same state is a no-op.
    # A malicious WM cannot forge a mac, so its entire remaining freedom is to replay a
    # state this wallet genuinely reached -- and this is what bounds which ones.
    if counter < await get_counter():
        raise DataError("attested counter is older than the stored counter")

    # ...and time must not run backwards either, beyond an allowance for clock jitter.
    # This catches an operator restored from a backup, which regresses the clock and the
    # counter together, and forces a forking WM to keep time monotone on every branch. It
    # does not constrain a hostile WM, which simply lies about the time.
    if timestamp < await get_timestamp() - EPSILON_SECONDS:
        raise DataError("attested time is older than the stored time")

    sync_round.set_attested(counter, mac, timestamp)
    return WardIngestAttestationAck(counter=counter)
