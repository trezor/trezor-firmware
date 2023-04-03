"""
All inputs set. Defining range signature parameters.
If in the applicable offloading mode, generate commitment masks.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import MoneroTransactionAllInputsSetAck

    from apps.monero.layout import MoneroTransactionProgress

    from .state import State


def all_inputs_set(
    state: State, progress: MoneroTransactionProgress
) -> MoneroTransactionAllInputsSetAck:
    from trezor.messages import MoneroTransactionAllInputsSetAck

    from apps.monero.xmr import crypto

    state.mem_trace(0)

    progress.step(state, state.STEP_ALL_IN)

    if state.last_step != state.STEP_VINI:
        raise ValueError("Invalid state transition")
    if state.current_input_index != state.input_count - 1:
        raise ValueError("Invalid input count")

    # The sum of the masks must match the input masks sum.
    state.sumout = crypto.Scalar()
    state.last_step = state.STEP_ALL_IN
    resp = MoneroTransactionAllInputsSetAck()
    return resp
