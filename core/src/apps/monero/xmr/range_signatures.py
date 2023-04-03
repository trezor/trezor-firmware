"""
Computes range signature

Can compute Bulletproof. Borromean support was discontinued.
Also can verify Bulletproof, in case the computation was offloaded.

Mostly ported from official Monero client, but also inspired by Mininero.
Author: Dusan Klinec, ph4r05, 2018
"""

import gc
from typing import TYPE_CHECKING

from apps.monero.xmr import crypto

if TYPE_CHECKING:
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import BulletproofPlus


def prove_range_bp_batch(
    amounts: list[int], masks: list[crypto.Scalar]
) -> BulletproofPlus:
    """Calculates Bulletproof in batches"""
    from apps.monero.xmr import bulletproof as bp

    bpi = bp.BulletProofPlusBuilder()
    bp_proof = bpi.prove_batch([crypto.Scalar(a) for a in amounts], masks)
    del (bpi, bp)
    gc.collect()

    return bp_proof


def verify_bp(
    bp_proof: BulletproofPlus,
    amounts: list[int],
    masks: list[crypto.Scalar],
) -> bool:
    """Verifies Bulletproof"""
    from apps.monero.xmr import bulletproof as bp
    from apps.monero.xmr import crypto_helpers

    if amounts:
        bp_proof.V = []
        for i in range(len(amounts)):
            C = crypto.gen_commitment_into(None, masks[i], amounts[i])
            crypto.scalarmult_into(C, C, crypto_helpers.INV_EIGHT_SC)
            bp_proof.V.append(crypto_helpers.encodepoint(C))

    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import BulletproofPlus

    assert isinstance(bp_proof, BulletproofPlus)
    bpi = bp.BulletProofPlusBuilder()
    res = bpi.verify(bp_proof)
    gc.collect()
    return res
