"""
Computes range signature

Can compute Bulletproof. Borromean support was discontinued.
Also can verify Bulletproof, in case the computation was offloaded.

Mostly ported from official Monero client, but also inspired by Mininero.
Author: Dusan Klinec, ph4r05, 2018
"""

import gc

from apps.monero.xmr import crypto


def prove_range_bp_batch(amounts, masks):
    """Calculates Bulletproof in batches"""
    from apps.monero.xmr import bulletproof as bp

    bpi = bp.BulletProofBuilder()
    bp_proof = bpi.prove_batch([crypto.sc_init(a) for a in amounts], masks)
    del (bpi, bp)
    gc.collect()

    return bp_proof


def verify_bp(bp_proof, amounts, masks):
    """Verifies Bulletproof"""
    from apps.monero.xmr import bulletproof as bp

    if amounts:
        bp_proof.V = []
        for i in range(len(amounts)):
            C = crypto.gen_commitment(masks[i], amounts[i])
            crypto.scalarmult_into(C, C, crypto.sc_inv_eight())
            bp_proof.V.append(crypto.encodepoint(C))

    bpi = bp.BulletProofBuilder()
    res = bpi.verify(bp_proof)
    gc.collect()
    return res
