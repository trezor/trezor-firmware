#
# Copyright (c) 2015 David Keijser <keijser@gmail.com>
# Copyright (c) 2016 Pavol Rusnak <stick@gk2.sk>
#
# Licensed under MIT License
#
# Implementations of Base58 and Base58Check encodings that are compatible
# with the bitcoin network.
#
# This module is based upon base58 snippets found scattered over many bitcoin
# tools written in python. From what I gather the original source is from a
# forum post by Gavin Andresen, so direct your praise to him.
# This module adds shiny packaging and support for python3.
#

# 58 character alphabet used
_alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def encode(data: bytes, alphabet=_alphabet) -> str:
    """
    Convert bytes to base58 encoded string.
    """
    origlen = len(data)
    data = data.lstrip(b"\0")
    newlen = len(data)

    p, acc = 1, 0
    for c in reversed(data):
        acc += p * c
        p = p << 8

    result = ""
    while acc > 0:
        acc, mod = divmod(acc, 58)
        result += alphabet[mod]

    return "".join((c for c in reversed(result + alphabet[0] * (origlen - newlen))))


def decode(string: str, alphabet=_alphabet) -> bytes:
    """
    Convert base58 encoded string to bytes.
    """
    origlen = len(string)
    string = string.lstrip(alphabet[0])
    newlen = len(string)

    p, acc = 1, 0
    for c in reversed(string):
        acc += p * alphabet.index(c)
        p *= 58

    result = []
    while acc > 0:
        acc, mod = divmod(acc, 256)
        result.append(mod)

    return bytes((b for b in reversed(result + [0] * (origlen - newlen))))


def sha256d_32(data: bytes) -> bytes:
    from .hashlib import sha256

    return sha256(sha256(data).digest()).digest()[:4]


def groestl512d_32(data: bytes) -> bytes:
    from .hashlib import groestl512

    return groestl512(groestl512(data).digest()).digest()[:4]


def encode_check(data: bytes, digestfunc=sha256d_32) -> str:
    """
    Convert bytes to base58 encoded string, append checksum.
    """
    return encode(data + digestfunc(data))


def decode_check(string: str, digestfunc=sha256d_32) -> bytes:
    """
    Convert base58 encoded string to bytes and verify checksum.
    """
    result = decode(string)
    return verify_checksum(result, digestfunc)


def verify_checksum(data: bytes, digestfunc) -> bytes:
    digestlen = len(digestfunc(b""))
    result, check = data[:-digestlen], data[-digestlen:]

    if check != digestfunc(result):
        raise ValueError("Invalid checksum")

    return result
