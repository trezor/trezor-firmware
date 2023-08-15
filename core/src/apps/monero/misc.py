from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.enums import MoneroNetworkType

    from apps.common.keychain import Keychain
    from apps.common.paths import Bip32Path

    from .xmr.credentials import AccountCreds
    from .xmr.crypto import Scalar


def get_creds(
    keychain: Keychain, address_n: Bip32Path, network_type: MoneroNetworkType
) -> AccountCreds:
    from apps.monero.xmr import monero
    from apps.monero.xmr.credentials import AccountCreds

    node = keychain.derive(address_n)

    key_seed = node.private_key()
    spend_sec, _, view_sec, _ = monero.generate_monero_keys(key_seed)

    creds = AccountCreds.new_wallet(view_sec, spend_sec, network_type)
    return creds


def compute_tx_key(
    spend_key_private: Scalar,
    tx_prefix_hash: bytes,
    salt: bytes,
    rand_mult_num: Scalar,
) -> bytes:
    from apps.monero.xmr import crypto, crypto_helpers

    rand_inp = crypto.sc_add_into(None, spend_key_private, rand_mult_num)
    passwd = crypto_helpers.keccak_2hash(
        crypto_helpers.encodeint(rand_inp) + tx_prefix_hash
    )
    tx_key = crypto_helpers.compute_hmac(salt, passwd)
    return tx_key


def compute_enc_key_host(
    view_key_private: Scalar, tx_prefix_hash: bytes
) -> tuple[bytes, bytes]:
    from trezor.crypto import random

    from apps.monero.xmr import crypto_helpers

    salt = random.bytes(32)
    passwd = crypto_helpers.keccak_2hash(
        crypto_helpers.encodeint(view_key_private) + tx_prefix_hash
    )
    tx_key = crypto_helpers.compute_hmac(salt, passwd)
    return tx_key, salt
