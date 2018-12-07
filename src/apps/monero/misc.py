from apps.common import HARDENED


def get_creds(keychain, address_n=None, network_type=None):
    from apps.monero.xmr import crypto, monero
    from apps.monero.xmr.credentials import AccountCreds

    use_slip0010 = 0 not in address_n  # If path contains 0 it is not SLIP-0010

    if use_slip0010:
        curve = "ed25519"
    else:
        curve = "secp256k1"
    node = keychain.derive(address_n, curve)

    if use_slip0010:
        key_seed = node.private_key()
    else:
        key_seed = crypto.cn_fast_hash(node.private_key())
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
