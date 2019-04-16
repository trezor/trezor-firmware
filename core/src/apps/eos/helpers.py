from trezor.messages import EosAsset

from apps.common import HARDENED


def eos_name_to_string(value) -> str:
    charmap = ".12345abcdefghijklmnopqrstuvwxyz"
    tmp = value
    string = ""
    for i in range(0, 13):
        c = charmap[tmp & (0x0F if i == 0 else 0x1F)]
        string = c + string
        tmp >>= 4 if i == 0 else 5

    return string.rstrip(".")


def eos_asset_to_string(asset: EosAsset) -> str:
    symbol_bytes = int.to_bytes(asset.symbol, 8, "big")
    precision = symbol_bytes[7]
    symbol = bytes(reversed(symbol_bytes[:7])).rstrip(b"\x00").decode("ascii")

    amount_digits = str(asset.amount)
    if precision > 0:
        integer, fraction = amount_digits[:-precision], amount_digits[-precision:]
        return "{}.{} {}".format(integer, fraction, symbol)
    else:
        return "{} {}".format(amount_digits, symbol)


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/194'/a'/0/0,
    where `a` is an account index from 0 to 1 000 000.
    Similar to Ethereum this should be 44'/194'/a', but for
    compatibility with other HW vendors we use 44'/194'/a'/0/0.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 194 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    if path[3] != 0:
        return False
    if path[4] != 0:
        return False
    return True
