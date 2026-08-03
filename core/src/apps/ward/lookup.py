from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDLookup, WARDLookupAck


async def lookup(msg: WARDLookup) -> WARDLookupAck:
    """WARDLookup wire handler (TA): verify a membership / non-membership proof
    against the device's authenticated root, via Core (ungated) into the WARD
    trust anchor (apps.ward.service). Shared verification with the update path and
    the on-device label lookup (apps.common.ward.lookup_label).
    """
    from trezor.messages import WARDLookupAck

    from apps.common import ward as core

    valid, counter, membership, wallet_id, ward_id = await core.lookup(
        msg.app_id,
        msg.address,
        msg.nonce,
        msg.tag,
        msg.ct,
        msg.proof,
        key_type=msg.key_type or "address",
        device_id=msg.device_id or 0,
        witness_entry_key=msg.witness_entry_key,
        witness_commit=msg.witness_commit,
    )

    return WARDLookupAck(
        valid=valid,
        counter=counter,
        membership=membership,
        wallet_id=wallet_id,
        ward_id=ward_id,
    )
