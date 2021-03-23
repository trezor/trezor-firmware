"""
This step serves for an incremental hashing of tx.vin[i] to the tx_prefix_hasher
after the sorting on tx.vin[i].ki. The sorting order was received in the previous step.
"""

from apps.monero.layout import confirms
from apps.monero.signing import offloading_keys
from apps.monero.xmr import crypto

from .state import State

if False:
    from trezor.messages import (
        MoneroTransactionInputViniAck,
        MoneroTransactionSourceEntry,
    )


async def input_vini(
    state: State,
    src_entr: MoneroTransactionSourceEntry,
    vini_bin: bytes,
    vini_hmac: bytes,
    orig_idx: int,
) -> MoneroTransactionInputViniAck:
    from trezor.messages import MoneroTransactionInputViniAck

    await confirms.transaction_step(
        state, state.STEP_VINI, state.current_input_index + 1
    )
    if state.last_step not in (state.STEP_INP, state.STEP_PERM, state.STEP_VINI):
        raise ValueError("Invalid state transition")
    if state.current_input_index >= state.input_count:
        raise ValueError("Too many inputs")

    if state.client_version >= 2 and state.last_step < state.STEP_VINI:
        state.current_input_index = -1
        state.last_ki = None

    state.current_input_index += 1

    # HMAC(T_in,i || vin_i)
    hmac_vini_comp = offloading_keys.gen_hmac_vini(
        state.key_hmac,
        src_entr,
        vini_bin,
        state.source_permutation[state.current_input_index]
        if state.client_version <= 1
        else orig_idx,
    )
    if not crypto.ct_equals(hmac_vini_comp, vini_hmac):
        raise ValueError("HMAC is not correct")

    # Key image sorting check - permutation correctness
    cur_ki = offloading_keys.get_ki_from_vini(vini_bin)
    if state.current_input_index > 0 and state.last_ki <= cur_ki:
        raise ValueError("Key image order invalid")

    """
    Incremental hasing of tx.vin[i]
    """
    state.tx_prefix_hasher.buffer(vini_bin)
    state.last_step = state.STEP_VINI
    state.last_ki = cur_ki if state.current_input_index < state.input_count else None
    return MoneroTransactionInputViniAck()
