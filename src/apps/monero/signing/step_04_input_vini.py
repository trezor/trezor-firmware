"""
This step successively hashes the inputs in the order
received in the previous step.
Also hashes `pseudo_out` to the final_message.
"""

from .state import State

from apps.monero.layout import confirms
from apps.monero.signing import offloading_keys
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
):
    """
    This step serves for an incremental hashing of tx.vin[i] to the tx_prefix_hasher
    after the sorting on tx.vin[i].ki.

    Originally, this step also incrementaly hashed pseudo_output[i] to the full_message_hasher for
    RctSimple transactions with Borromean proofs (HF8).

    In later hard-forks, the pseudo_outputs were moved to the rctsig.prunable
    which is not hashed to the final signature, thus pseudo_output hashing has been removed
    (as we support only HF9 and HF10 now).
    """
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
    return MoneroTransactionInputViniAck()
