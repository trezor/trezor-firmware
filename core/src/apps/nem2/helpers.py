from micropython import const

from apps.common import HARDENED

NEM_NETWORK_MAINNET = const(0x68)
NEM_NETWORK_TESTNET = const(0x98)
NEM_NETWORK_MIJIN = const(0x60)

def check_path(path: list, network=None) -> bool:
    """
    Validates derivation path to fit 44'/43'/a' or 44'/43'/a'/0'/0',
    where `a` is an account number. We believe the path should be
    44'/43'/a', but for compatibility reasons with NEM's NanoWallet
    we allow 44'/43'/a'/0'/0' as well.
    Testnet is also allowed: 44'/1'/a'{/0'/0'}
    """
    length = len(path)
    if length != 3 and length != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if not (
        path[1] == 43 | HARDENED
        or (network == NEM_NETWORK_TESTNET and path[1] == 1 | HARDENED)
    ):
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    if length == 5 and (path[3] != 0 | HARDENED or path[4] != 0 | HARDENED):
        return False
    return True
