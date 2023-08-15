"""
Final message, signatures were already returned in the previous step.

Here we return private tx keys in encrypted form using transaction specific key,
derived from tx hash and the private spend key. The key is deterministic,
so we can recover it just from the transaction and the spend key.

The private tx keys are used in other numerous Monero features.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import MoneroTransactionFinalAck

    from .state import State


def final_msg(state: State) -> MoneroTransactionFinalAck:
    from trezor.crypto import random
    from trezor.messages import MoneroTransactionFinalAck

    from apps.monero import misc
    from apps.monero.xmr import chacha_poly, crypto, crypto_helpers

    if state.last_step != state.STEP_SIGN:
        raise ValueError("Invalid state transition")
    if state.current_input_index != state.input_count - 1:
        raise ValueError("Invalid input count")

    # _compute_tx_key
    salt = random.bytes(32)
    rand_mult_num = crypto.random_scalar()
    rand_mult = crypto_helpers.encodeint(rand_mult_num)
    tx_key = misc.compute_tx_key(
        state.creds.spend_key_private, state.tx_prefix_hash, salt, rand_mult_num
    )

    key_buff = crypto_helpers.encodeint(state.tx_priv) + b"".join(
        [crypto_helpers.encodeint(x) for x in state.additional_tx_private_keys]
    )
    tx_enc_keys = chacha_poly.encrypt_pack(tx_key, key_buff)
    state.last_step = None

    return MoneroTransactionFinalAck(
        cout_key=None,
        salt=salt,
        rand_mult=rand_mult,
        tx_enc_keys=tx_enc_keys,
        opening_key=state.opening_key,
    )
