"""
All inputs set. Defining range signature parameters.
If in the applicable offloading mode, generate commitment masks.
"""

from .state import State

from apps.monero.layout import confirms
from apps.monero.xmr import crypto


async def all_inputs_set(state: State):
    state.mem_trace(0)

    await confirms.transaction_step(state.ctx, state.STEP_ALL_IN)

    from trezor.messages.MoneroTransactionAllInputsSetAck import (
        MoneroTransactionAllInputsSetAck,
    )

    # Generate random commitment masks to be used in range proofs.
    # If SimpleRCT is used the sum of the masks must match the input masks sum.
    state.sumout = crypto.sc_init(0)
    rsig_data = None

    # Client 0, HF9. Non-deterministic masks
    if not state.is_det_mask():
        rsig_data = await _compute_masks(state)

    resp = MoneroTransactionAllInputsSetAck(rsig_data=rsig_data)
    return resp


async def _compute_masks(state: State):
    """
    Output masks computed in advance. Used with client_version=0 && HF9.
    After HF10 (included) masks are deterministic, computed from the amount_key.

    After all client update to v1 this code will be removed.
    In order to preserve client_version=0 compatibility the masks have to be adjusted.
    """
    from trezor.messages.MoneroTransactionRsigData import MoneroTransactionRsigData
    from apps.monero.signing import offloading_keys

    rsig_data = MoneroTransactionRsigData()

    # If range proofs are being offloaded, we send the masks to the host, which uses them
    # to create the range proof. If not, we do not send any and we use them in the following step.
    if state.rsig_offload:
        rsig_data.mask = []

    # Deterministic masks, the last one is computed to balance the sums
    for i in range(state.output_count):
        if i + 1 == state.output_count:
            cur_mask = crypto.sc_sub(state.sumpouts_alphas, state.sumout)
            state.output_last_mask = cur_mask
        else:
            cur_mask = offloading_keys.det_comm_masks(state.key_enc, i)

        crypto.sc_add_into(state.sumout, state.sumout, cur_mask)

        if state.rsig_offload:
            rsig_data.mask.append(crypto.encodeint(cur_mask))

    if not crypto.sc_eq(state.sumpouts_alphas, state.sumout):
        raise ValueError("Sum eq error")

    state.sumout = crypto.sc_init(0)
    return rsig_data
