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

    valid, counter, membership, wallet_id = await core.lookup(
        msg.address,
        msg.value,
        msg.proof,
        witness_address=msg.witness_address,
        witness_value=msg.witness_value,
        counter=msg.counter,
        witness_counter=msg.witness_counter,
    )

    return WARDLookupAck(
        valid=valid,
        counter=counter,
        membership=membership,
        wallet_id=wallet_id,
    )
