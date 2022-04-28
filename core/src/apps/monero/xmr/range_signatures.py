"""
Computes range signature

Can compute Bulletproof. Borromean support was discontinued.
Also can verify Bulletproof, in case the computation was offloaded.

Mostly ported from official Monero client, but also inspired by Mininero.
Author: Dusan Klinec, ph4r05, 2018
"""

import gc
from typing import TYPE_CHECKING

from apps.monero.xmr import crypto, crypto_helpers

if TYPE_CHECKING:
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import (
        Bulletproof,
        BulletproofPlus,
    )


def prove_range_bp_batch(
    amounts: list[int], masks: list[crypto.Scalar], bp_plus: bool = False
) -> Bulletproof | BulletproofPlus:
    """Calculates Bulletproof in batches"""
    from apps.monero.xmr import bulletproof as bp

    bpi = bp.BulletProofPlusBuilder() if bp_plus else bp.BulletProofBuilder()
    bp_proof = bpi.prove_batch([crypto.Scalar(a) for a in amounts], masks)
    del (bpi, bp)
    gc.collect()

    return bp_proof


def verify_bp(
    bp_proof: Bulletproof | BulletproofPlus,
    amounts: list[int],
    masks: list[crypto.Scalar],
) -> bool:
    """Verifies Bulletproof"""
    from apps.monero.xmr import bulletproof as bp

    if amounts:
        bp_proof.V = []
        for i in range(len(amounts)):
            C = crypto.gen_commitment_into(None, masks[i], amounts[i])
            crypto.scalarmult_into(C, C, crypto_helpers.INV_EIGHT_SC)
            bp_proof.V.append(crypto_helpers.encodepoint(C))

    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import BulletproofPlus

    bpi = (
        bp.BulletProofPlusBuilder()
        if isinstance(bp_proof, BulletproofPlus)
        else bp.BulletProofBuilder()
    )
    res = bpi.verify(bp_proof)
    gc.collect()
    return res
