"""
Final message, signatures were already returned in the previous step.

Here we return private tx keys in encrypted form using transaction specific key,
derived from tx hash and the private spend key. The key is deterministic,
so we can recover it just from the transaction and the spend key.

The private tx keys are used in other numerous Monero features.
"""

from trezor.messages.MoneroTransactionFinalAck import MoneroTransactionFinalAck

from .state import State

from apps.monero.xmr import crypto
from apps.monero.xmr.crypto import chacha_poly


async def final_msg(state: State):
    tx_key, salt, rand_mult = _compute_tx_key(
        state.creds.spend_key_private, state.tx_prefix_hash
    )

    key_buff = crypto.encodeint(state.tx_priv) + b"".join(
        [crypto.encodeint(x) for x in state.additional_tx_private_keys]
    )
    tx_enc_keys = chacha_poly.encrypt_pack(tx_key, key_buff)

    return MoneroTransactionFinalAck(
        cout_key=None, salt=salt, rand_mult=rand_mult, tx_enc_keys=tx_enc_keys
    )


def _compute_tx_key(spend_key_private, tx_prefix_hash):
    salt = crypto.random_bytes(32)

    rand_mult_num = crypto.random_scalar()
    rand_mult = crypto.encodeint(rand_mult_num)

    rand_inp = crypto.sc_add(spend_key_private, rand_mult_num)
    passwd = crypto.keccak_2hash(crypto.encodeint(rand_inp) + tx_prefix_hash)
    tx_key = crypto.compute_hmac(salt, passwd)
    return tx_key, salt, rand_mult
