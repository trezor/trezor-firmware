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
    from apps.ward.caller import host_caller

    # The domain, key type and slot are the WARD service's, not the host's.
    caller = host_caller(msg.app_id, msg.key_type, msg.device_id)
    pull = (
        msg.content is None
        and msg.identity is None
        and not msg.proof
        and msg.witness_entry_key is None
        and msg.witness_commit is None
    )

    if pull:
        valid, counter, membership, _wallet_id, ward_id = await core.lookup_pull(
            caller, bytes(msg.address)
        )
    else:
        m_val = core.read_leaf_content(msg.content)
        _m_kt, m_id = core.read_leaf_identity(msg.identity)
        valid, counter, membership, _wallet_id, ward_id = await core.lookup(
            caller,
            bytes(msg.address),
            m_id,
            m_val,
            [bytes(node) for node in msg.proof],
            witness_entry_key=(
                bytes(msg.witness_entry_key)
                if msg.witness_entry_key is not None
                else None
            ),
            witness_commit=(
                bytes(msg.witness_commit) if msg.witness_commit is not None else None
            ),
        )

    return WARDLookupAck(
        valid=valid,
        counter=counter,
        membership=membership,
        ward_id=ward_id,
    )
