from micropython import const

from trezor import wire
from trezor.crypto import base58
from trezor.crypto.curve import ed25519, nist256p1, secp256k1

TEZOS_AMOUNT_DIVISIBILITY = const(6)

PREFIXES = {
    # addresses
    "tz1": [6, 161, 159],
    "tz2": [6, 161, 161],
    "tz3": [6, 161, 164],
    "KT1": [2, 90, 121],
    # public keys
    "edpk": [13, 15, 37, 217],
    "sppk": [3, 254, 226, 86],
    "p2pk": [3, 178, 139, 127],
    # signatures
    "edsig": [9, 245, 205, 134, 18],
    "spsig1": [13, 115, 101, 19, 63],
    "p2sig": [54, 240, 44, 52],
    # operation hash
    "o": [5, 116],
}

TEZOS_CURVES = [
    {
        "name": "ed25519",
        "address_prefix": "tz1",
        "pk_prefix": "edpk",
        "sig_prefix": "edsig",
        "sig_remove_first_byte": False,
        "module": ed25519,
    },
    {
        "name": "secp256k1",
        "address_prefix": "tz2",
        "pk_prefix": "sppk",
        "sig_prefix": "spsig1",
        "sig_remove_first_byte": True,
        "module": secp256k1,
    },
    {
        "name": "nist256p1",
        "address_prefix": "tz3",
        "pk_prefix": "p2pk",
        "sig_prefix": "p2sig",
        "sig_remove_first_byte": True,
        "module": nist256p1,
    },
]


def get_curve_name(index):
    if 0 <= index < len(TEZOS_CURVES):
        return TEZOS_CURVES[index]["name"]
    raise wire.DataError("Invalid type of curve")


def get_curve_module(curve):
    return TEZOS_CURVES[curve]["module"]


def get_address_prefix(curve):
    return TEZOS_CURVES[curve]["address_prefix"]


def get_pk_prefix(curve):
    return TEZOS_CURVES[curve]["pk_prefix"]


def get_sig_prefix(curve):
    return TEZOS_CURVES[curve]["sig_prefix"]


def check_sig_remove_first_byte(curve):
    return TEZOS_CURVES[curve]["sig_remove_first_byte"]


def b58cencode(payload, prefix=None):
    result = payload
    if prefix is not None:
        result = bytes(PREFIXES[prefix]) + payload
    return base58.encode_check(result)


def b58cdecode(enc, prefix=None):
    decoded = base58.decode_check(enc)
    if prefix is not None:
        decoded = decoded[len(PREFIXES[prefix]) :]
    return decoded
