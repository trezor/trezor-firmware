"""
Generates a MLSAG signature for one input.
"""

import gc

from trezor import utils

from .state import State

from apps.monero.layout import confirms
from apps.monero.xmr import crypto

if False:
    from trezor.messages.MoneroTransactionSourceEntry import (
        MoneroTransactionSourceEntry,
    )


async def sign_input(
    state: State,
    src_entr: MoneroTransactionSourceEntry,
    vini_bin: bytes,
    vini_hmac: bytes,
    pseudo_out: bytes,
    pseudo_out_hmac: bytes,
    pseudo_out_alpha_enc: bytes,
    spend_enc: bytes,
):
    """
    Signing UTXO.

    Mask Balancing.
    Sum of input masks has to be equal to the sum of output masks.
    As the output masks has been made deterministic in HF10 the mask sum equality is corrected
    in this step. The last input mask (and thus pseudo_out) is recomputed so the sums equal.

    If deterministic masks cannot be used (client_version=0), the balancing is done in step 5
    on output masks as pseudo outputs have to remain same.

    :param state: transaction state
    :param src_entr: Source entry
    :param vini_bin: tx.vin[i] for the transaction. Contains key image, offsets, amount (usually zero)
    :param vini_hmac: HMAC for the tx.vin[i] as returned from Trezor
    :param pseudo_out: Pedersen commitment for the current input, uses pseudo_out_alpha
                       as a mask. Only applicable for RCTTypeSimple.
    :param pseudo_out_hmac: HMAC for pseudo_out
    :param pseudo_out_alpha_enc: alpha mask used in pseudo_out, only applicable for RCTTypeSimple. Encrypted.
    :param spend_enc: one time address spending private key. Encrypted.
    :return: Generated signature MGs[i]
    """
    await confirms.transaction_step(
        state.ctx, state.STEP_SIGN, state.current_input_index + 1, state.input_count
    )

    state.current_input_index += 1
    if state.current_input_index >= state.input_count:
        raise ValueError("Invalid inputs count")
    if pseudo_out is None:
        raise ValueError("SimpleRCT requires pseudo_out but none provided")
    if pseudo_out_alpha_enc is None:
        raise ValueError("SimpleRCT requires pseudo_out's mask but none provided")

    input_position = state.source_permutation[state.current_input_index]
    mods = utils.unimport_begin()

    # Check input's HMAC
    from apps.monero.signing import offloading_keys

    vini_hmac_comp = await offloading_keys.gen_hmac_vini(
        state.key_hmac, src_entr, vini_bin, input_position
    )
    if not crypto.ct_equals(vini_hmac_comp, vini_hmac):
        raise ValueError("HMAC is not correct")

    gc.collect()
    state.mem_trace(1, True)

    from apps.monero.xmr.crypto import chacha_poly

    pseudo_out_alpha = crypto.decodeint(
        chacha_poly.decrypt_pack(
            offloading_keys.enc_key_txin_alpha(state.key_enc, input_position),
            bytes(pseudo_out_alpha_enc),
        )
    )

    # Last pseud_out is recomputed so mask sums hold
    if state.is_det_mask() and input_position + 1 == state.input_count:
        # Recompute the lash alpha so the sum holds
        state.mem_trace("Correcting alpha")
        alpha_diff = crypto.sc_sub(state.sumout, state.sumpouts_alphas)
        crypto.sc_add_into(pseudo_out_alpha, pseudo_out_alpha, alpha_diff)
        pseudo_out_c = crypto.gen_commitment(pseudo_out_alpha, state.input_last_amount)

    else:
        if input_position + 1 == state.input_count:
            utils.ensure(
                crypto.sc_eq(state.sumpouts_alphas, state.sumout), "Sum eq error"
            )

        # both pseudo_out and its mask were offloaded so we need to
        # validate pseudo_out's HMAC and decrypt the alpha
        pseudo_out_hmac_comp = crypto.compute_hmac(
            offloading_keys.hmac_key_txin_comm(state.key_hmac, input_position),
            pseudo_out,
        )
        if not crypto.ct_equals(pseudo_out_hmac_comp, pseudo_out_hmac):
            raise ValueError("HMAC is not correct")

        pseudo_out_c = crypto.decodepoint(pseudo_out)

    state.mem_trace(2, True)

    # Spending secret
    spend_key = crypto.decodeint(
        chacha_poly.decrypt_pack(
            offloading_keys.enc_key_spend(state.key_enc, input_position),
            bytes(spend_enc),
        )
    )

    del (
        offloading_keys,
        chacha_poly,
        pseudo_out,
        pseudo_out_hmac,
        pseudo_out_alpha_enc,
        spend_enc,
    )
    utils.unimport_end(mods)
    state.mem_trace(3, True)

    from apps.monero.xmr.serialize_messages.ct_keys import CtKey

    # Basic setup, sanity check
    index = src_entr.real_output
    input_secret_key = CtKey(dest=spend_key, mask=crypto.decodeint(src_entr.mask))
    kLRki = None  # for multisig: src_entr.multisig_kLRki

    # Private key correctness test
    utils.ensure(
        crypto.point_eq(
            crypto.decodepoint(src_entr.outputs[src_entr.real_output].key.dest),
            crypto.scalarmult_base(input_secret_key.dest),
        ),
        "Real source entry's destination does not equal spend key's",
    )
    utils.ensure(
        crypto.point_eq(
            crypto.decodepoint(src_entr.outputs[src_entr.real_output].key.commitment),
            crypto.gen_commitment(input_secret_key.mask, src_entr.amount),
        ),
        "Real source entry's mask does not equal spend key's",
    )

    state.mem_trace(4, True)

    from apps.monero.xmr import mlsag

    mg_buffer = []
    ring_pubkeys = [x.key for x in src_entr.outputs]
    del src_entr

    mlsag.generate_mlsag_simple(
        state.full_message,
        ring_pubkeys,
        input_secret_key,
        pseudo_out_alpha,
        pseudo_out_c,
        kLRki,
        index,
        mg_buffer,
    )

    del (input_secret_key, pseudo_out_alpha, mlsag, ring_pubkeys)
    state.mem_trace(5, True)

    from trezor.messages.MoneroTransactionSignInputAck import (
        MoneroTransactionSignInputAck,
    )

    return MoneroTransactionSignInputAck(
        signature=mg_buffer, pseudo_out=crypto.encodepoint(pseudo_out_c)
    )
