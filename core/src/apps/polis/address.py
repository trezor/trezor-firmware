from trezor import wire
from apps.common import HARDENED, paths

"""
We believe Polis should use 44'/1997'/a for everything, because it is
account-based, rather than UTXO-based. 
"""


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/60'/i',
    where `i` is an address index from 0 to 1 000 000.
    """
    if len(path) > 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1997 | HARDENED:
        return False
    if path[2] > 1000000:
        return False
    return True