"""
Computes range signature

Can compute Borromean range proof or Bulletproof.
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


def prove_range_borromean(amount, last_mask):
    """Calculates Borromean range proof"""
    # The large chunks allocated first to avoid potential memory fragmentation issues.
    ai = bytearray(32 * 64)
    alphai = bytearray(32 * 64)
    Cis = bytearray(32 * 64)
    s0s = bytearray(32 * 64)
    s1s = bytearray(32 * 64)
    buff = bytearray(32)
    ee_bin = bytearray(32)

    a = crypto.sc_init(0)
    si = crypto.sc_init(0)
    c = crypto.sc_init(0)
    ee = crypto.sc_init(0)
    tmp_ai = crypto.sc_init(0)
    tmp_alpha = crypto.sc_init(0)

    C_acc = crypto.identity()
    C_h = crypto.xmr_H()
    C_tmp = crypto.identity()
    L = crypto.identity()
    kck = crypto.get_keccak()

    for ii in range(64):
        crypto.random_scalar(tmp_ai)
        if last_mask is not None and ii == 63:
            crypto.sc_sub_into(tmp_ai, last_mask, a)

        crypto.sc_add_into(a, a, tmp_ai)
        crypto.random_scalar(tmp_alpha)

        crypto.scalarmult_base_into(L, tmp_alpha)
        crypto.scalarmult_base_into(C_tmp, tmp_ai)

        # if 0: C_tmp += Zero (nothing is added)
        # if 1: C_tmp += 2^i*H
        # 2^i*H is already stored in C_h
        if (amount >> ii) & 1 == 1:
            crypto.point_add_into(C_tmp, C_tmp, C_h)

        crypto.point_add_into(C_acc, C_acc, C_tmp)

        # Set Ci[ii] to sigs
        crypto.encodepoint_into(Cis, C_tmp, ii << 5)
        crypto.encodeint_into(ai, tmp_ai, ii << 5)
        crypto.encodeint_into(alphai, tmp_alpha, ii << 5)

        if ((amount >> ii) & 1) == 0:
            crypto.random_scalar(si)
            crypto.encodepoint_into(buff, L)
            crypto.hash_to_scalar_into(c, buff)

            crypto.point_sub_into(C_tmp, C_tmp, C_h)
            crypto.add_keys2_into(L, si, c, C_tmp)

            crypto.encodeint_into(s1s, si, ii << 5)

        crypto.encodepoint_into(buff, L)
        kck.update(buff)

        crypto.point_double_into(C_h, C_h)

    # Compute ee
    tmp_ee = kck.digest()
    crypto.decodeint_into(ee, tmp_ee)
    del (tmp_ee, kck)

    C_h = crypto.xmr_H()
    gc.collect()

    # Second pass, s0, s1
    for ii in range(64):
        crypto.decodeint_into(tmp_alpha, alphai, ii << 5)
        crypto.decodeint_into(tmp_ai, ai, ii << 5)

        if ((amount >> ii) & 1) == 0:
            crypto.sc_mulsub_into(si, tmp_ai, ee, tmp_alpha)
            crypto.encodeint_into(s0s, si, ii << 5)

        else:
            crypto.random_scalar(si)
            crypto.encodeint_into(s0s, si, ii << 5)

            crypto.decodepoint_into(C_tmp, Cis, ii << 5)
            crypto.add_keys2_into(L, si, ee, C_tmp)
            crypto.encodepoint_into(buff, L)
            crypto.hash_to_scalar_into(c, buff)

            crypto.sc_mulsub_into(si, tmp_ai, c, tmp_alpha)
            crypto.encodeint_into(s1s, si, ii << 5)

        crypto.point_double_into(C_h, C_h)

    crypto.encodeint_into(ee_bin, ee)

    del (ai, alphai, buff, tmp_ai, tmp_alpha, si, c, ee, C_tmp, C_h, L)
    gc.collect()

    return C_acc, a, [s0s, s1s, ee_bin, Cis]
