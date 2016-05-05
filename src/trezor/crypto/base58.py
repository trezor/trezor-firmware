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

from .hashlib import sha256

# 58 character alphabet used
_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def encode(data: bytes) -> str:
    origlen = len(data)
    data = data.lstrip(b'\0')
    newlen = len(data)

    p, acc = 1, 0
    for c in reversed(data):
        acc += p * c
        p = p << 8

    result = ''
    while acc > 0:
        acc, mod = divmod(acc, 58)
        result += _alphabet[mod]

    return ''.join([c for c in reversed(result + _alphabet[0] * (origlen - newlen))])


def decode(string: str) -> bytes:
    origlen = len(string)
    string = string.lstrip(_alphabet[0])
    newlen = len(string)

    p, acc = 1, 0
    for c in reversed(string):
        acc += p * _alphabet.index(c)
        p *= 58

    result = []
    while acc > 0:
        acc, mod = divmod(acc, 256)
        result.append(mod)

    return bytes([b for b in reversed(result +[0] * (origlen - newlen))])


def encode_check(data: bytes) -> str:
    digest = sha256(sha256(data).digest()).digest()
    return encode(data + digest[:4])


def decode_check(string: str) -> bytes:
    result = decode(string)
    result, check = result[:-4], result[-4:]
    digest = sha256(sha256(result).digest()).digest()

    if check != digest[:4]:
        raise ValueError("Invalid checksum")

    return result
