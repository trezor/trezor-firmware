from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDConfirmRevertByWM, WARDConfirmRevertByWMAck


async def confirm_revert(msg: WARDConfirmRevertByWM) -> WARDConfirmRevertByWMAck:
    """WARDConfirmRevertByWM wire handler (TA): install a one-step rollback after the
    WM co-signs the demoted head. Verifies the WM signature over (to_counter, mac) and
    re-verifies the stored AuthRevert, then installs the predecessor at the forward-
    incremented counter.
    """
    from trezor.messages import WARDConfirmRevertByWMAck

    from apps.common import ward as core

    counter, root, ward_id, root_mac = await core.finalize_revert(
        msg.counter, msg.mac, msg.wm_signature
    )

    return WARDConfirmRevertByWMAck(
        counter=counter, new_root=root, ward_id=ward_id, root_mac=root_mac
    )
