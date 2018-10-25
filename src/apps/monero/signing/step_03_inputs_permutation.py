"""
Inputs in transaction need to be sorted by their key image, otherwise the
transaction is rejected. The sorting is done on host and then sent here in
the MoneroTransactionInputsPermutationRequest message.

The message contains just a simple array where each item stands for the
input's position in the transaction.

We do not do the actual sorting here (we do not store the complete input
data anyway, so we can't) we just save the array to the state and use
it later when needed.
"""

from .state import State

from apps.monero.layout.confirms import transaction_step


async def tsx_inputs_permutation(state: State, permutation: list):
    from trezor.messages.MoneroTransactionInputsPermutationAck import (
        MoneroTransactionInputsPermutationAck,
    )

    await transaction_step(state.ctx, state.STEP_PERM)

    """
    Set permutation on the inputs - sorted by key image on host.
    """
    if len(permutation) != state.input_count:
        raise ValueError("Invalid permutation size")
    _check_permutation(permutation)

    state.source_permutation = permutation
    state.current_input_index = -1

    return MoneroTransactionInputsPermutationAck()


def _check_permutation(permutation):
    for n in range(len(permutation)):
        if n not in permutation:
            raise ValueError("Invalid permutation")
