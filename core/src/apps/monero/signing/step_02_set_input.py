"""
UTXOs are sent one by one to Trezor for processing, encoded as MoneroTransactionSourceEntry.

MoneroTransactionSourceEntry contains the actual UTXO to be spent, but also the other decoy/mixin
outputs. So all the outputs are in one list and then the `real_output` index specifies which output
is the real one to be spent.

This step computes spending secret key, key image, tx.vin[i] + HMAC, Pedersen commitment on amount.

If number of inputs is small, in-memory mode is used = alpha, pseudo_outs are kept in the Trezor.
Otherwise pseudo_outs are offloaded with HMAC, alpha is offloaded encrypted under chacha_poly with
key derived for exactly this purpose.
"""
from apps.monero.layout import confirms
from apps.monero.xmr import crypto, monero, serialize

from .state import State

if False:
    from apps.monero.xmr.types import Sc25519, Ge25519
    from trezor.messages import MoneroTransactionSourceEntry
    from trezor.messages import MoneroTransactionSetInputAck


async def set_input(
    state: State, src_entr: MoneroTransactionSourceEntry
) -> MoneroTransactionSetInputAck:
    from trezor.messages import MoneroTransactionSetInputAck
    from apps.monero.xmr.crypto import chacha_poly
    from apps.monero.xmr.serialize_messages.tx_prefix import TxinToKey
    from apps.monero.signing import offloading_keys

    state.current_input_index += 1

    await confirms.transaction_step(state, state.STEP_INP, state.current_input_index)

    if state.last_step > state.STEP_INP:
        raise ValueError("Invalid state transition")
    if state.current_input_index >= state.input_count:
        raise ValueError("Too many inputs")
    # real_output denotes which output in outputs is the real one (ours)
    if src_entr.real_output >= len(src_entr.outputs):
        raise ValueError(
            "real_output index %s bigger than output_keys.size() %s"
            % (src_entr.real_output, len(src_entr.outputs))
        )
    state.summary_inputs_money += src_entr.amount

    # Secrets derivation
    # the UTXO's one-time address P
    out_key = crypto.decodepoint(src_entr.outputs[src_entr.real_output].key.dest)
    # the tx_pub of our UTXO stored inside its transaction
    tx_key = crypto.decodepoint(src_entr.real_out_tx_key)
    additional_tx_pub_key = _get_additional_public_key(src_entr)

    """
    Calculates `derivation = Ra`, private spend key `x = H(Ra||i) + b` to be able
    to spend the UTXO; and key image `I = x*H(P||i)`
    """
    xi, ki, di = monero.generate_tx_spend_and_key_image_and_derivation(
        state.creds,
        state.subaddresses,
        out_key,
        tx_key,
        additional_tx_pub_key,
        src_entr.real_output_in_tx_index,
        state.account_idx,
        src_entr.subaddr_minor,
    )
    state.mem_trace(1, True)

    # Construct tx.vin
    # If multisig is used then ki in vini should be src_entr.multisig_kLRki.ki
    vini = TxinToKey(amount=src_entr.amount, k_image=crypto.encodepoint(ki))
    vini.key_offsets = _absolute_output_offsets_to_relative(
        [x.idx for x in src_entr.outputs]
    )

    if src_entr.rct:
        vini.amount = 0

    """
    Serialize `vini` with variant code for TxinToKey (prefix = TxinToKey.VARIANT_CODE).
    The binary `vini_bin` is later sent to step 4 and 9 with its hmac,
    where it is checked and directly used.
    """
    vini_bin = serialize.dump_msg(vini, preallocate=64, prefix=b"\x02")
    state.mem_trace(2, True)

    # HMAC(T_in,i || vin_i)
    hmac_vini = offloading_keys.gen_hmac_vini(
        state.key_hmac, src_entr, vini_bin, state.current_input_index
    )
    state.mem_trace(3, True)

    # PseudoOuts commitment, alphas stored to state
    alpha, pseudo_out = _gen_commitment(state, src_entr.amount)
    pseudo_out = crypto.encodepoint(pseudo_out)

    # The alpha is encrypted and passed back for storage
    pseudo_out_hmac = crypto.compute_hmac(
        offloading_keys.hmac_key_txin_comm(state.key_hmac, state.current_input_index),
        pseudo_out,
    )

    alpha_enc = chacha_poly.encrypt_pack(
        offloading_keys.enc_key_txin_alpha(state.key_enc, state.current_input_index),
        crypto.encodeint(alpha),
    )

    spend_enc = chacha_poly.encrypt_pack(
        offloading_keys.enc_key_spend(state.key_enc, state.current_input_index),
        crypto.encodeint(xi),
    )

    state.last_step = state.STEP_INP
    if state.current_input_index + 1 == state.input_count:
        """
        When we finish the inputs processing, we no longer need
        the precomputed subaddresses so we clear them to save memory.
        """
        state.subaddresses = None
        state.input_last_amount = src_entr.amount

    return MoneroTransactionSetInputAck(
        vini=vini_bin,
        vini_hmac=hmac_vini,
        pseudo_out=pseudo_out,
        pseudo_out_hmac=pseudo_out_hmac,
        pseudo_out_alpha=alpha_enc,
        spend_key=spend_enc,
    )


def _gen_commitment(state: State, in_amount: int) -> tuple[Sc25519, Ge25519]:
    """
    Computes Pedersen commitment - pseudo outs
    Here is slight deviation from the original protocol.
    We want that \\sum Alpha = \\sum A_{i,j} where A_{i,j} is a mask from range proof for output i, bit j.

    Previously this was computed in such a way that Alpha_{last} = \\sum A{i,j} - \\sum_{i=0}^{last-1} Alpha
    But we would prefer to compute commitment before range proofs so alphas are generated completely randomly
    and the last A mask is computed in this special way.
    Returns pseudo_out
    """
    alpha = crypto.random_scalar()
    state.sumpouts_alphas = crypto.sc_add(state.sumpouts_alphas, alpha)
    return alpha, crypto.gen_commitment(alpha, in_amount)


def _absolute_output_offsets_to_relative(off: list[int]) -> list[int]:
    """
    Mixin outputs are specified in relative numbers. First index is absolute
    and the rest is an offset of a previous one.
    Helps with varint encoding size.

    Example: absolute {7,11,15,20} is converted to {7,4,4,5}
    """
    if len(off) == 0:
        return off
    off.sort()
    for i in range(len(off) - 1, 0, -1):
        off[i] -= off[i - 1]
    return off


def _get_additional_public_key(
    src_entr: MoneroTransactionSourceEntry,
) -> Ge25519 | None:
    additional_tx_pub_key = None
    if len(src_entr.real_out_additional_tx_keys) == 1:  # compression
        additional_tx_pub_key = crypto.decodepoint(
            src_entr.real_out_additional_tx_keys[0]
        )
    elif src_entr.real_out_additional_tx_keys:
        if src_entr.real_output_in_tx_index >= len(
            src_entr.real_out_additional_tx_keys
        ):
            raise ValueError("Wrong number of additional derivations")
        additional_tx_pub_key = crypto.decodepoint(
            src_entr.real_out_additional_tx_keys[src_entr.real_output_in_tx_index]
        )
    return additional_tx_pub_key
