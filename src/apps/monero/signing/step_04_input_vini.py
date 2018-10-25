"""
This step successively hashes the inputs in the order
received in the previous step.
Also hashes `pseudo_out` to the final_message.
"""

from .state import State

from apps.monero.layout import confirms
from apps.monero.signing import RctType, RsigType, offloading_keys
from apps.monero.xmr import crypto

if False:
    from trezor.messages.MoneroTransactionSourceEntry import (
        MoneroTransactionSourceEntry,
    )


async def input_vini(
    state: State,
    src_entr: MoneroTransactionSourceEntry,
    vini_bin: bytes,
    vini_hmac: bytes,
    pseudo_out: bytes,
    pseudo_out_hmac: bytes,
):
    from trezor.messages.MoneroTransactionInputViniAck import (
        MoneroTransactionInputViniAck,
    )

    await confirms.transaction_step(
        state.ctx, state.STEP_VINI, state.current_input_index + 1, state.input_count
    )
    if state.current_input_index >= state.input_count:
        raise ValueError("Too many inputs")

    state.current_input_index += 1

    # HMAC(T_in,i || vin_i)
    hmac_vini_comp = await offloading_keys.gen_hmac_vini(
        state.key_hmac,
        src_entr,
        vini_bin,
        state.source_permutation[state.current_input_index],
    )
    if not crypto.ct_equals(hmac_vini_comp, vini_hmac):
        raise ValueError("HMAC is not correct")

    """
    Incremental hasing of tx.vin[i]
    """
    state.tx_prefix_hasher.buffer(vini_bin)

    # in monero version >= 8 pseudo outs were moved to a different place
    # bulletproofs imply version >= 8
    if state.rct_type == RctType.Simple and state.rsig_type != RsigType.Bulletproof:
        _hash_vini_pseudo_out(state, pseudo_out, pseudo_out_hmac)

    return MoneroTransactionInputViniAck()


def _hash_vini_pseudo_out(state: State, pseudo_out: bytes, pseudo_out_hmac: bytes):
    """
    Incremental hasing of pseudo output. Only applicable for simple rct.
    """
    idx = state.source_permutation[state.current_input_index]
    pseudo_out_hmac_comp = crypto.compute_hmac(
        offloading_keys.hmac_key_txin_comm(state.key_hmac, idx), pseudo_out
    )
    if not crypto.ct_equals(pseudo_out_hmac, pseudo_out_hmac_comp):
        raise ValueError("HMAC invalid for pseudo outs")

    state.full_message_hasher.set_pseudo_out(pseudo_out)
