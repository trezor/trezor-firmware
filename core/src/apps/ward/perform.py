from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDPerformUpdate, WARDPerformUpdateAck


async def perform(msg: WARDPerformUpdate) -> WARDPerformUpdateAck:
    """WARDPerformUpdate wire handler (TA): authorize a queued intent. Core pulls
    the proof on demand (WARDProofRequest -> WARDProofAck) and the trust anchor
    verifies it and computes the candidate (root_T, mac_T). The counter is not
    advanced here.
    """
    from trezor.messages import WARDPerformUpdateAck

    from apps.common import ward as core

    (
        counter,
        root,
        mac,
        _wallet_id,
        ward_id,
        entry_key,
        key_type,
        id_part,
        val_part,
    ) = await core.perform(msg.pending_id)

    return WARDPerformUpdateAck(
        counter=counter,
        new_root=root,
        mac=mac,
        ward_id=ward_id,
        entry_key=entry_key,
        content=core.make_leaf_content(val_part),
        identity=core.make_leaf_identity(key_type, id_part),
    )
