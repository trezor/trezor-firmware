from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDIngestAttestation, WARDIngestAttestationAck


async def ingest_attestation(msg: WARDIngestAttestation) -> WARDIngestAttestationAck:
    """WARDIngestAttestation wire handler (TA): verify + record the WM freshness
    attestation for the open sync round via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDIngestAttestationAck

    from apps.common import ward as core

    counter, wallet_id = await core.ingest_attestation(
        msg.counter, msg.mac, msg.wm_signature
    )

    return WARDIngestAttestationAck(counter=counter, wallet_id=wallet_id)
