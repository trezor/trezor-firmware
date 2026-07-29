from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDConfirmedByWM, WARDConfirmedByWMAck


async def finalize(msg: WARDConfirmedByWM) -> WARDConfirmedByWMAck:
    """WARDConfirmedByWM wire handler (TA): install the committed candidate after
    the WM has signed it (via Core -> WARD trust anchor). Verifies the WM signature
    over the exact device-derived (counter_T, mac_T), installs root_T, advances the
    counter, and drops the queued edit.
    """
    from trezor.messages import WARDConfirmedByWMAck

    from apps.common import ward as core

    counter, root, wallet_id, root_mac = await core.finalize(
        msg.counter, msg.mac, msg.wm_signature, msg.pending_id
    )

    return WARDConfirmedByWMAck(
        counter=counter, new_root=root, wallet_id=wallet_id, root_mac=root_mac
    )
