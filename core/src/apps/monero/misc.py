from apps.common import HARDENED

if False:
    from typing import Tuple
    from apps.monero.xmr.types import Sc25519


def get_creds(keychain, address_n=None, network_type=None):
    from apps.monero.xmr import monero
    from apps.monero.xmr.credentials import AccountCreds

    node = keychain.derive(address_n)

    key_seed = node.private_key()
    spend_sec, _, view_sec, _ = monero.generate_monero_keys(key_seed)

    creds = AccountCreds.new_wallet(view_sec, spend_sec, network_type)
    return creds


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/128'/a',
    where `a` is an account index from 0 to 1 000 000.
    """
    if len(path) != 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 128 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    return True


def compute_tx_key(
    spend_key_private: Sc25519,
    tx_prefix_hash: bytes,
    salt: bytes,
    rand_mult_num: Sc25519,
) -> bytes:
    from apps.monero.xmr import crypto

    rand_inp = crypto.sc_add(spend_key_private, rand_mult_num)
    passwd = crypto.keccak_2hash(crypto.encodeint(rand_inp) + tx_prefix_hash)
    tx_key = crypto.compute_hmac(salt, passwd)
    return tx_key


def compute_enc_key_host(
    view_key_private: Sc25519, tx_prefix_hash: bytes
) -> Tuple[bytes, bytes]:
    from apps.monero.xmr import crypto

    salt = crypto.random_bytes(32)
    passwd = crypto.keccak_2hash(crypto.encodeint(view_key_private) + tx_prefix_hash)
    tx_key = crypto.compute_hmac(salt, passwd)
    return tx_key, salt
