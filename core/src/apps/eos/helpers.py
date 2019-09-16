from trezor import wire
from trezor.crypto import base58
from trezor.messages.EosAsset import EosAsset

from apps.common import HARDENED


def base58_encode(prefix: str, sig_prefix: str, data: bytes) -> str:
    b58 = base58.encode(data + base58.ripemd160_32(data + sig_prefix.encode()))
    if sig_prefix:
        return prefix + sig_prefix + "_" + b58
    else:
        return prefix + b58


def eos_name_to_string(value: int) -> str:
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

    amount_digits = "{:0{precision}d}".format(asset.amount, precision=precision)
    if precision > 0:
        integer = amount_digits[:-precision]
        if integer == "":
            integer = "0"
        fraction = amount_digits[-precision:]

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


def public_key_to_wif(pub_key: bytes) -> str:
    if pub_key[0] == 0x04 and len(pub_key) == 65:
        head = b"\x03" if pub_key[64] & 0x01 else b"\x02"
        compressed_pub_key = head + pub_key[1:33]
    elif pub_key[0] in [0x02, 0x03] and len(pub_key) == 33:
        compressed_pub_key = pub_key
    else:
        raise wire.DataError("invalid public key")
    return base58_encode("EOS", "", compressed_pub_key)
