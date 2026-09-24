from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardIngestAttestation, WardIngestAttestationAck


async def ingest(msg: WardIngestAttestation) -> WardIngestAttestationAck:
    """Verify the WM's attestation of the transition that reached the current head.

    ADOPTS NOTHING, and the root arriving here changes none of that. The attestation says a
    trusted authority calls this head current; it does not say the wallet ever produced it, since
    the WM signs roots in the clear and could sign one it invented. What turns it into a statement
    about state is the LINK or the CHAIN folded against it later, in `reconcile` or `verify_chain`.
    This step establishes freshness and nothing else.
    """
    from trezor.messages import WardIngestAttestationAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import verify_round_attestation
    from .common import require_initialized
    from .root import get_counter

    require_initialized()

    from_counter, from_root, counter, root = await verify_round_attestation(
        msg.from_counter,
        msg.from_root or None,
        msg.to_counter,
        msg.to_root or None,
        msg.timestamp or 0,
        msg.wm_signature,
    )

    # Anti-rollback, and the reason this rule lives HERE rather than in the shared check:
    # `recover` needs the opposite one. The attested counter may not precede the floor this
    # wallet has already accepted; equality is fine, since re-reading the same state is a no-op.
    # It is also the only bound left on a WM that lies: it can now name a root this wallet never
    # held, so the floor is what stops it naming an OLD one and freezing the device there.
    if counter < await get_counter():
        raise DataError("attested counter is older than the stored counter")

    sync_round.set_attested(from_counter, from_root, counter, root)
    return WardIngestAttestationAck(counter=counter)
