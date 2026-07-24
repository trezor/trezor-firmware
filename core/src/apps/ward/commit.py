from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDCommitCandidate, WARDCommitCandidateAck


async def commit(msg: WARDCommitCandidate) -> WARDCommitCandidateAck:
    """WARDCommitCandidate wire handler (TA): emit the queued candidate triple
    (root_T, counter_T, mac_T) via the WARD trust anchor (through Core). The
    counter is not advanced here.
    """
    from trezor.messages import WARDCommitCandidateAck

    from apps.common import ward as core

    counter, root, mac, wallet_id = await core.commit()

    return WARDCommitCandidateAck(
        counter=counter, new_root=root, mac=mac, wallet_id=wallet_id
    )
