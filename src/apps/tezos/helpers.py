from micropython import const

from trezor import wire
from trezor.crypto import base58

TEZOS_CURVE = "ed25519"
TEZOS_AMOUNT_DIVISIBILITY = const(6)
TEZOS_ORIGINATED_ADDRESS_PREFIX = "KT1"
TEZOS_PUBLICKEY_PREFIX = "edpk"
TEZOS_SIGNATURE_PREFIX = "edsig"
TEZOS_PREFIX_BYTES = {
    # addresses
    "tz1": [6, 161, 159],
    "tz2": [6, 161, 161],
    "tz3": [6, 161, 164],
    "KT1": [2, 90, 121],
    # public keys
    "edpk": [13, 15, 37, 217],
    # signatures
    "edsig": [9, 245, 205, 134, 18],
    # operation hash
    "o": [5, 116],
}


def tezos_get_address_prefix(tag):
    prefixes = ["tz1", "tz2", "tz3"]
    if 0 <= tag < len(prefixes):
        return prefixes[tag]
    raise wire.DataError("Invalid tag in address hash")


def b58cencode(payload, prefix=None):
    result = payload
    if prefix is not None:
        result = bytes(TEZOS_PREFIX_BYTES[prefix]) + payload
    return base58.encode_check(result)


def b58cdecode(enc, prefix=None):
    decoded = base58.decode_check(enc)
    if prefix is not None:
        decoded = decoded[len(TEZOS_PREFIX_BYTES[prefix]) :]
    return decoded
