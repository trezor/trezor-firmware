"""
This step serves for an incremental hashing of tx.vin[i] to the tx_prefix_hasher
after the sorting on tx.vin[i].ki. The sorting order was received in the previous step.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import (
        MoneroTransactionInputViniAck,
        MoneroTransactionSourceEntry,
    )

    from apps.monero.layout import MoneroTransactionProgress

    from .state import State


def input_vini(
    state: State,
    src_entr: MoneroTransactionSourceEntry,
    vini_bin: bytes,
    vini_hmac: bytes,
    orig_idx: int,
    progress: MoneroTransactionProgress,
) -> MoneroTransactionInputViniAck:
    from trezor.messages import MoneroTransactionInputViniAck

    from apps.monero.signing import offloading_keys
    from apps.monero.xmr import crypto

    STEP_VINI = state.STEP_VINI  # local_cache_attribute

    progress.step(state, STEP_VINI, state.current_input_index + 1)
    if state.last_step not in (state.STEP_INP, STEP_VINI):
        raise ValueError("Invalid state transition")
    if state.current_input_index >= state.input_count:
        raise ValueError("Too many inputs")

    if state.last_step < STEP_VINI:
        state.current_input_index = -1
        state.last_ki = None

    state.current_input_index += 1

    # HMAC(T_in,i || vin_i)
    hmac_vini_comp = offloading_keys.gen_hmac_vini(
        state.key_hmac,
        src_entr,
        vini_bin,
        orig_idx,
    )
    if not crypto.ct_equals(hmac_vini_comp, vini_hmac):
        raise ValueError("HMAC is not correct")

    # Key image sorting check - permutation correctness
    cur_ki = offloading_keys.get_ki_from_vini(vini_bin)
    if state.current_input_index > 0 and state.last_ki <= cur_ki:
        raise ValueError("Key image order invalid")

    # Incremental hasing of tx.vin[i]
    state.tx_prefix_hasher.buffer(vini_bin)
    state.last_step = STEP_VINI
    state.last_ki = cur_ki if state.current_input_index < state.input_count else None
    return MoneroTransactionInputViniAck()
