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
        msg.from_head_nonce,
        msg.to_counter,
        msg.to_root or None,
        msg.to_head_nonce,
        msg.timestamp or 0,
        msg.wm_signature,
    )

    # Anti-rollback. The attested counter may not precede the floor this wallet has already
    # accepted; equality is fine, since re-reading the same state is a no-op. It is also the only
    # bound left on a WM that lies: it can now name a root this wallet never held, so the floor is
    # what stops it naming an OLD one and freezing the device there.
    #
    # THE ONE EXEMPTION IS A DEMOTION THE USER APPROVED, and it is exact twice over: `rollback`
    # records the whole transition it minted a REVERT for AND the head the device stood on when
    # the user held to confirm, and only that pair passes. A demotion is the one operation whose
    # purpose is to come down, so the floor cannot be what decides it -- but nothing else may
    # inherit the exemption.
    #
    # WHY THE STEP ALONE IS NOT ENOUGH. The screen counts the discarded changes from the device's
    # own head, so consent is about a descent FROM that head. An authorisation left alive while
    # the device moved on would exempt the same endpoints from a floor that had risen, and the
    # user would get a descent discarding more changes than the one they approved. `adopt` spends
    # the authorisation on every adoption for the same reason; this is the half that does not
    # depend on remembering to.
    stored = await get_counter()
    if counter < stored and not sync_round.demotion_matches(
        stored, from_counter, from_root, counter, root
    ):
        raise DataError("attested counter is older than the stored counter")

    sync_round.set_attested(from_counter, from_root, counter, root)
    return WardIngestAttestationAck(counter=counter)
