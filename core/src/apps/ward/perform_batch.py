from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDPerformBatch, WARDPerformBatchAck


async def perform_batch(msg: WARDPerformBatch) -> WARDPerformBatchAck:
    """WARDPerformBatch wire handler (TA): authorize N queued intents as ONE root
    transition. Core pulls a pre-state proof per intent (WARDProofRequest ->
    WARDProofAck, one per entry_key) and the trust anchor folds them into a single
    successor root (counter += 1 for the whole batch), stamps every leaf, and
    authenticates the transition with head_mac + AuthCommit (+ Ed25519 SigCommit when
    WARD_KSIG). The counter is not advanced here.
    """
    from trezor.messages import WARDBatchLeaf, WARDPerformBatchAck

    from apps.common import ward as core
    from apps.ward import service

    (
        counter,
        from_root,
        to_root,
        mac,
        head_mac,
        auth_commit,
        sig,
        wallet_id,
        ward_id,
        leaves,
    ) = await core.perform_batch(list(msg.pending_ids))

    return WARDPerformBatchAck(
        counter=counter,
        from_root=from_root,  # 32B MAC-preimage form (EMPTY_ROOT_HASH if empty)
        new_root=to_root,
        mac=mac,
        wallet_id=wallet_id,
        ward_id=ward_id,
        head_mac=head_mac,
        auth_commit=auth_commit,
        # SigCommit is present only when the benchmark flag is on; omit otherwise.
        sig_commit=(sig if (sig and service.WARD_KSIG) else None),
        leaves=[
            WARDBatchLeaf(
                entry_key=ek,
                entry_type=entry_type,
                nonce=nonce,
                tag=tag,
                ct=ct,
            )
            for (ek, entry_type, nonce, tag, ct) in leaves
        ],
    )
