from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDIngestAttestation, WARDIngestAttestationAck


async def ingest(msg: WARDIngestAttestation) -> WARDIngestAttestationAck:
    """WARDIngestAttestation wire handler (TA): verify + record the WM freshness
    attestation for the open sync round via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDIngestAttestationAck

    from apps.common import ward as core

    counter, _wallet_id = await core.ingest(
        msg.counter,
        bytes(msg.mac) if msg.mac is not None else None,
        bytes(msg.wm_signature),
        msg.timestamp,
        bytes(msg.head_nonce),
    )

    return WARDIngestAttestationAck(counter=counter)
