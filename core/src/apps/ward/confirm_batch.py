from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDConfirmBatchByWM, WARDConfirmBatchByWMAck


async def confirm_batch(msg: WARDConfirmBatchByWM) -> WARDConfirmBatchByWMAck:
    """WARDConfirmBatchByWM wire handler (TA): install a committed batch after the WM
    has co-signed its head. Verifies the WM signature over the exact device-derived
    (to_counter, mac_t), re-verifies the stored AuthCommit, checks anti-rollback,
    installs to_root, advances the counter by one, and drops the whole pending set.
    """
    from trezor.messages import WARDConfirmBatchByWMAck

    from apps.common import ward as core

    counter, root, ward_id, root_mac = await core.finalize_batch(
        msg.counter, msg.mac, msg.wm_signature
    )

    return WARDConfirmBatchByWMAck(
        counter=counter, new_root=root, ward_id=ward_id, root_mac=root_mac
    )
