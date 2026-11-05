from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDLookup, WARDLookupAck


async def lookup(msg: WARDLookup) -> WARDLookupAck:
    """WARDLookup wire handler (TA): verify a (membership / non-membership) proof
    against the device's authenticated root, via Core (ungated) into the WARD trust
    anchor (apps.ward.service).

    Two modes, by what the host supplied:
      - PUSH: the host attached proof material (the leaf's two parts for membership,
        or a witness). Verify it as-is.
      - PULL: the host attached NO proof material -> the device computes the target
        entry_key itself and pulls the proof (WARDProofRequest), so even a
        non-membership verdict for an absent address is device-proven (the host
        cannot form the target entry_key). This is what wardVerify (dblookup) drives.
    """
    from trezor.messages import WARDLookupAck

    from apps.common import ward as core

    key_type = msg.key_type or "address"
    device_id = msg.device_id or 0
    pull = msg.content is None and msg.witness_entry_key is None

    if pull:
        valid, counter, membership, _wallet_id, ward_id = await core.lookup_pull(
            msg.app_id, msg.address, key_type=key_type, device_id=device_id
        )
    else:
        m_val = core.read_leaf_content(msg.content)
        _m_kt, m_id = core.read_leaf_identity(msg.identity)
        valid, counter, membership, _wallet_id, ward_id = await core.lookup(
            msg.app_id,
            msg.address,
            m_id,
            m_val,
            msg.proof,
            key_type=key_type,
            device_id=device_id,
            witness_entry_key=msg.witness_entry_key,
            witness_commit=msg.witness_commit,
        )

    return WARDLookupAck(
        valid=valid,
        counter=counter,
        membership=membership,
        ward_id=ward_id,
    )
