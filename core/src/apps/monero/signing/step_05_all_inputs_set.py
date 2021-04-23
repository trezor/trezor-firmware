"""
All inputs set. Defining range signature parameters.
If in the applicable offloading mode, generate commitment masks.
"""

from apps.monero.layout import confirms
from apps.monero.xmr import crypto

from .state import State

if False:
    from trezor.messages import MoneroTransactionAllInputsSetAck


async def all_inputs_set(state: State) -> MoneroTransactionAllInputsSetAck:
    state.mem_trace(0)

    await confirms.transaction_step(state, state.STEP_ALL_IN)

    from trezor.messages import MoneroTransactionAllInputsSetAck

    if state.last_step != state.STEP_VINI:
        raise ValueError("Invalid state transition")
    if state.current_input_index != state.input_count - 1:
        raise ValueError("Invalid input count")

    # The sum of the masks must match the input masks sum.
    state.sumout = crypto.sc_init(0)
    state.last_step = state.STEP_ALL_IN
    resp = MoneroTransactionAllInputsSetAck()
    return resp
