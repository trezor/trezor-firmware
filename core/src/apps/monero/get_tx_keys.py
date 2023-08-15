"""
This `get_tx_key` command supports retrieval of private tx keys (not spend keys,
just random transaction privates `r` and additional private keys if applicable)
required by users to check the transaction or when resolving disputes with
the recipient.

It supports returning transaction derivations = private tx key * public view key.
This enables to compute the tx_proof for outgoing transactions which are also
a nice tool when resolving disputes, provides better protection as tx private
key are not exported in this case.

This is related to singing/step10 where we send `tx_enc_keys` to the host
encrypted using the private spend key. Here the host sends it back
in `MoneroGetTxKeyRequest.tx_enc_keys` to be decrypted and yet again encrypted
using the view key, which the host possess.
"""
from micropython import const
from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

_GET_TX_KEY_REASON_TX_DERIVATION = const(1)

if TYPE_CHECKING:
    from trezor.messages import MoneroGetTxKeyAck, MoneroGetTxKeyRequest

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_tx_keys(
    msg: MoneroGetTxKeyRequest, keychain: Keychain
) -> MoneroGetTxKeyAck:
    from trezor import utils, wire
    from trezor.messages import MoneroGetTxKeyAck

    from apps.common import paths
    from apps.monero import layout, misc
    from apps.monero.xmr import chacha_poly, crypto, crypto_helpers

    await paths.validate_path(keychain, msg.address_n)

    do_deriv = msg.reason == _GET_TX_KEY_REASON_TX_DERIVATION
    await layout.require_confirm_tx_key(export_key=not do_deriv)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)

    tx_enc_key = misc.compute_tx_key(
        creds.spend_key_private,
        msg.tx_prefix_hash,
        msg.salt1,
        crypto_helpers.decodeint(msg.salt2),
    )

    # the plain_buff first stores the tx_priv_keys as decrypted here
    # and then is used to store the derivations if applicable
    plain_buff = chacha_poly.decrypt_pack(tx_enc_key, msg.tx_enc_keys)
    utils.ensure(len(plain_buff) % 32 == 0, "Tx key buffer has invalid size")
    msg.tx_enc_keys = b""

    # If return only derivations do tx_priv * view_pub
    if do_deriv:
        if msg.view_public_key is None:
            raise wire.DataError("Missing view public key")

        plain_buff = bytearray(plain_buff)
        view_pub = crypto_helpers.decodepoint(msg.view_public_key)
        tx_priv = crypto.Scalar()
        derivation = crypto.Point()
        n_keys = len(plain_buff) // 32
        for c in range(n_keys):
            crypto.decodeint_into(tx_priv, plain_buff, 32 * c)
            crypto.scalarmult_into(derivation, view_pub, tx_priv)
            crypto.encodepoint_into(plain_buff, derivation, 32 * c)

    # Encrypt by view-key based password.
    tx_enc_key_host, salt = misc.compute_enc_key_host(
        creds.view_key_private, msg.tx_prefix_hash
    )

    res = chacha_poly.encrypt_pack(tx_enc_key_host, plain_buff)
    res_msg = MoneroGetTxKeyAck(salt=salt)
    if do_deriv:
        res_msg.tx_derivations = res
        return res_msg

    res_msg.tx_keys = res
    return res_msg
