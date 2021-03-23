"""
Final message, signatures were already returned in the previous step.

Here we return private tx keys in encrypted form using transaction specific key,
derived from tx hash and the private spend key. The key is deterministic,
so we can recover it just from the transaction and the spend key.

The private tx keys are used in other numerous Monero features.
"""

from trezor.messages import MoneroTransactionFinalAck

from apps.monero import misc
from apps.monero.xmr import crypto
from apps.monero.xmr.crypto import chacha_poly

from .state import State

if False:
    from apps.monero.xmr.types import Sc25519


def final_msg(state: State) -> MoneroTransactionFinalAck:
    if state.last_step != state.STEP_SIGN:
        raise ValueError("Invalid state transition")
    if state.current_input_index != state.input_count - 1:
        raise ValueError("Invalid input count")

    tx_key, salt, rand_mult = _compute_tx_key(
        state.creds.spend_key_private, state.tx_prefix_hash
    )

    key_buff = crypto.encodeint(state.tx_priv) + b"".join(
        [crypto.encodeint(x) for x in state.additional_tx_private_keys]
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


def _compute_tx_key(
    spend_key_private: Sc25519, tx_prefix_hash: bytes
) -> tuple[bytes, bytes, bytes]:
    salt = crypto.random_bytes(32)

    rand_mult_num = crypto.random_scalar()
    rand_mult = crypto.encodeint(rand_mult_num)

    tx_key = misc.compute_tx_key(spend_key_private, tx_prefix_hash, salt, rand_mult_num)
    return tx_key, salt, rand_mult
