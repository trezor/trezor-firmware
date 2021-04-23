"""
Inputs in transaction need to be sorted by their key image, otherwise the
transaction is rejected. The sorting is done on host and then sent here in
the MoneroTransactionInputsPermutationRequest message.

The message contains just a simple array where each item stands for the
input's position in the transaction.

We do not do the actual sorting here (we do not store the complete input
data anyway, so we can't) we just save the array to the state and use
it later when needed.

New protocol version (CL3) does not store the permutation. The permutation
correctness is checked by checking the number of elements,
HMAC correctness (host sends original sort idx) and ordering check
on the key images. This step is skipped.
"""

from apps.monero.layout.confirms import transaction_step

from .state import State

if False:
    from trezor.messages import MoneroTransactionInputsPermutationAck


async def tsx_inputs_permutation(
    state: State, permutation: list[int]
) -> MoneroTransactionInputsPermutationAck:
    from trezor.messages import MoneroTransactionInputsPermutationAck

    await transaction_step(state, state.STEP_PERM)

    """
    Set permutation on the inputs - sorted by key image on host.
    """
    if state.last_step != state.STEP_INP:
        raise ValueError("Invalid state transition")
    if len(permutation) != state.input_count:
        raise ValueError("Invalid permutation size")
    if state.current_input_index != state.input_count - 1:
        raise ValueError("Invalid input count")
    _check_permutation(permutation)

    state.source_permutation = permutation
    state.current_input_index = -1
    state.last_step = state.STEP_PERM

    return MoneroTransactionInputsPermutationAck()


def _check_permutation(permutation: list[int]):
    for n in range(len(permutation)):
        if n not in permutation:
            raise ValueError("Invalid permutation")
