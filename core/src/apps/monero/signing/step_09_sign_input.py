"""
Generates a MLSAG signature for one input.

Mask Balancing.
Sum of input masks has to be equal to the sum of output masks.
As the output masks has been made deterministic in HF10 the mask sum equality is corrected
in this step. The last input mask (and thus pseudo_out) is recomputed so the sums equal.

If deterministic masks cannot be used (client_version=0), the balancing is done in step 5
on output masks as pseudo outputs have to remain same.
"""

import gc

from trezor import utils

from apps.monero.layout import confirms
from apps.monero.xmr import crypto

from .state import State

if False:
    from trezor.messages import MoneroTransactionSourceEntry
    from trezor.messages import MoneroTransactionSignInputAck


async def sign_input(
    state: State,
    src_entr: MoneroTransactionSourceEntry,
    vini_bin: bytes,
    vini_hmac: bytes,
    pseudo_out: bytes,
    pseudo_out_hmac: bytes,
    pseudo_out_alpha_enc: bytes,
    spend_enc: bytes,
    orig_idx: int,
) -> MoneroTransactionSignInputAck:
    """
    :param state: transaction state
    :param src_entr: Source entry
    :param vini_bin: tx.vin[i] for the transaction. Contains key image, offsets, amount (usually zero)
    :param vini_hmac: HMAC for the tx.vin[i] as returned from Trezor
    :param pseudo_out: Pedersen commitment for the current input, uses pseudo_out_alpha
                       as a mask. Only applicable for RCTTypeSimple.
    :param pseudo_out_hmac: HMAC for pseudo_out
    :param pseudo_out_alpha_enc: alpha mask used in pseudo_out, only applicable for RCTTypeSimple. Encrypted.
    :param spend_enc: one time address spending private key. Encrypted.
    :param orig_idx: original index of the src_entr before sorting (HMAC check)
    :return: Generated signature MGs[i]
    """
    await confirms.transaction_step(
        state, state.STEP_SIGN, state.current_input_index + 1
    )

    state.current_input_index += 1
    if state.last_step not in (state.STEP_ALL_OUT, state.STEP_SIGN):
        raise ValueError("Invalid state transition")
    if state.current_input_index >= state.input_count:
        raise ValueError("Invalid inputs count")
    if pseudo_out is None:
        raise ValueError("SimpleRCT requires pseudo_out but none provided")
    if pseudo_out_alpha_enc is None:
        raise ValueError("SimpleRCT requires pseudo_out's mask but none provided")

    input_position = (
        state.source_permutation[state.current_input_index]
        if state.client_version <= 1
        else orig_idx
    )
    mods = utils.unimport_begin()

    # Check input's HMAC
    from apps.monero.signing import offloading_keys

    vini_hmac_comp = offloading_keys.gen_hmac_vini(
        state.key_hmac, src_entr, vini_bin, input_position
    )
    if not crypto.ct_equals(vini_hmac_comp, vini_hmac):
        raise ValueError("HMAC is not correct")

    # Key image sorting check - permutation correctness
    cur_ki = offloading_keys.get_ki_from_vini(vini_bin)
    if state.current_input_index > 0 and state.last_ki <= cur_ki:
        raise ValueError("Key image order invalid")

    state.last_ki = cur_ki if state.current_input_index < state.input_count else None
    del (cur_ki, vini_bin, vini_hmac, vini_hmac_comp)

    gc.collect()
    state.mem_trace(1, True)

    from apps.monero.xmr.crypto import chacha_poly

    pseudo_out_alpha = crypto.decodeint(
        chacha_poly.decrypt_pack(
            offloading_keys.enc_key_txin_alpha(state.key_enc, input_position),
            bytes(pseudo_out_alpha_enc),
        )
    )

    # Last pseudo_out is recomputed so mask sums hold
    if input_position + 1 == state.input_count:
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

    # Basic setup, sanity check
    from apps.monero.xmr.serialize_messages.tx_ct_key import CtKey

    index = src_entr.real_output
    input_secret_key = CtKey(spend_key, crypto.decodeint(src_entr.mask))

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
    from apps.monero import signing

    mg_buffer = []
    ring_pubkeys = [x.key for x in src_entr.outputs if x]
    utils.ensure(len(ring_pubkeys) == len(src_entr.outputs), "Invalid ring")
    del src_entr

    state.mem_trace(5, True)

    if state.tx_type == signing.RctType.CLSAG:
        state.mem_trace("CLSAG")
        mlsag.generate_clsag_simple(
            state.full_message,
            ring_pubkeys,
            input_secret_key,
            pseudo_out_alpha,
            pseudo_out_c,
            index,
            mg_buffer,
        )
    else:
        mlsag.generate_mlsag_simple(
            state.full_message,
            ring_pubkeys,
            input_secret_key,
            pseudo_out_alpha,
            pseudo_out_c,
            index,
            mg_buffer,
        )

    del (CtKey, input_secret_key, pseudo_out_alpha, mlsag, ring_pubkeys)
    state.mem_trace(6, True)

    from trezor.messages import MoneroTransactionSignInputAck

    # Encrypt signature, reveal once protocol finishes OK
    if state.client_version >= 3:
        utils.unimport_end(mods)
        state.mem_trace(7, True)
        mg_buffer = _protect_signature(state, mg_buffer)

    state.mem_trace(8, True)
    state.last_step = state.STEP_SIGN
    return MoneroTransactionSignInputAck(
        signature=mg_buffer, pseudo_out=crypto.encodepoint(pseudo_out_c)
    )


def _protect_signature(state: State, mg_buffer: list[bytes]) -> list[bytes]:
    """
    Encrypts the signature with keys derived from state.opening_key.
    After protocol finishes without error, opening_key is sent to the
    host.
    """
    from trezor.crypto import random
    from trezor.crypto import chacha20poly1305
    from apps.monero.signing import offloading_keys

    if state.last_step != state.STEP_SIGN:
        state.opening_key = random.bytes(32)

    nonce = offloading_keys.key_signature(
        state.opening_key, state.current_input_index, True
    )[:12]

    key = offloading_keys.key_signature(
        state.opening_key, state.current_input_index, False
    )

    cipher = chacha20poly1305(key, nonce)

    """
    cipher.update() input has to be 512 bit long (besides the last block).
    Thus we go over mg_buffer and buffer 512 bit input blocks before
    calling cipher.update().
    """
    CHACHA_BLOCK = 64  # 512 bit chacha key-stream block size
    buff = bytearray(CHACHA_BLOCK)
    buff_len = 0  # valid bytes in the block buffer

    mg_len = 0
    for data in mg_buffer:
        mg_len += len(data)

    # Preallocate array of ciphertext blocks, ceil, add tag block
    mg_res = [None] * (1 + (mg_len + CHACHA_BLOCK - 1) // CHACHA_BLOCK)
    mg_res_c = 0
    for ix, data in enumerate(mg_buffer):
        data_ln = len(data)
        data_off = 0
        while data_ln > 0:
            to_add = min(CHACHA_BLOCK - buff_len, data_ln)
            if to_add:
                buff[buff_len : buff_len + to_add] = data[data_off : data_off + to_add]
                data_ln -= to_add
                buff_len += to_add
                data_off += to_add

            if len(buff) != CHACHA_BLOCK or buff_len > CHACHA_BLOCK:
                raise ValueError("Invariant error")

            if buff_len == CHACHA_BLOCK:
                mg_res[mg_res_c] = cipher.encrypt(buff)
                mg_res_c += 1
                buff_len = 0

        mg_buffer[ix] = None
        if ix & 7 == 0:
            gc.collect()

    # The last block can be incomplete
    if buff_len:
        mg_res[mg_res_c] = cipher.encrypt(buff[:buff_len])
        mg_res_c += 1

    mg_res[mg_res_c] = cipher.finish()
    return mg_res
