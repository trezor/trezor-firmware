from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDConfirmCommit, WARDConfirmCommitAck


async def confirm_commit(msg: WARDConfirmCommit) -> WARDConfirmCommitAck:
    """WARDConfirmCommit wire handler (TA): confirm the committed candidate with
    the WM signature via the WARD trust anchor (through Core). Installs root_T and
    advances the counter.
    """
    from trezor.messages import WARDConfirmCommitAck

    from apps.common import ward as core

    counter, root, wallet_id, root_mac = await core.confirm_commit(
        msg.counter, msg.mac, msg.qm_signature
    )

    return WARDConfirmCommitAck(
        counter=counter, new_root=root, wallet_id=wallet_id, root_mac=root_mac
    )
