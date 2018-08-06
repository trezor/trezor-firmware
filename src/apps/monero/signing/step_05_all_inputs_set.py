"""
All inputs set. Defining range signature parameters.
If in the applicable offloading mode, generate commitment masks.
"""

from trezor import utils

from .state import State

from apps.monero.layout import confirms
from apps.monero.signing import RctType
from apps.monero.xmr import crypto


async def all_inputs_set(state: State):
    state.mem_trace(0)

    await confirms.transaction_step(state.ctx, state.STEP_ALL_IN)

    from trezor.messages.MoneroTransactionAllInputsSetAck import (
        MoneroTransactionAllInputsSetAck,
    )
    from trezor.messages.MoneroTransactionRsigData import MoneroTransactionRsigData

    # Generate random commitment masks to be used in range proofs.
    # If SimpleRCT is used the sum of the masks must match the input masks sum.
    state.sumout = crypto.sc_init(0)
    for i in range(state.output_count):
        cur_mask = crypto.new_scalar()  # new mask for each output
        is_last = i + 1 == state.output_count
        if is_last and state.rct_type == RctType.Simple:
            # in SimpleRCT the last mask needs to be calculated as an offset of the sum
            crypto.sc_sub_into(cur_mask, state.sumpouts_alphas, state.sumout)
        else:
            crypto.random_scalar(cur_mask)

        crypto.sc_add_into(state.sumout, state.sumout, cur_mask)
        state.output_masks.append(cur_mask)

    if state.rct_type == RctType.Simple:
        utils.ensure(
            crypto.sc_eq(state.sumout, state.sumpouts_alphas), "Invalid masks sum"
        )  # sum check
    state.sumout = crypto.sc_init(0)

    rsig_data = MoneroTransactionRsigData()
    resp = MoneroTransactionAllInputsSetAck(rsig_data=rsig_data)

    # If range proofs are being offloaded, we send the masks to the host, which uses them
    # to create the range proof. If not, we do not send any and we use them in the following step.
    if state.rsig_offload:
        tmp_buff = bytearray(32)
        rsig_data.mask = bytearray(32 * state.output_count)
        for i in range(state.output_count):
            crypto.encodeint_into(tmp_buff, state.output_masks[i])
            utils.memcpy(rsig_data.mask, 32 * i, tmp_buff, 0, 32)

    return resp
