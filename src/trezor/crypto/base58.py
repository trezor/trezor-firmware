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
alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def encode(v):
    origlen = len(v)
    v = v.lstrip(b'\0')
    newlen = len(v)

    p, acc = 1, 0
    for c in reversed(v):
        acc += p * c
        p = p << 8

    result = ''
    while acc > 0:
        acc, mod = divmod(acc, 58)
        result += alphabet[mod]

    return ''.join([c for c in reversed(result + alphabet[0] * (origlen - newlen))])


def decode(v):
    origlen = len(v)
    v = v.lstrip(alphabet[0])
    newlen = len(v)

    p, acc = 1, 0
    for c in reversed(v):
        acc += p * alphabet.index(c)
        p *= 58

    result = []
    while acc > 0:
        acc, mod = divmod(acc, 256)
        result.append(mod)

    return bytes([b for b in reversed(result +[0] * (origlen - newlen))])


def encode_check(v):
    digest = sha256(sha256(v).digest()).digest()
    return encode(v + digest[:4])


def decode_check(v):
    result = decode(v)
    result, check = result[:-4], result[-4:]
    digest = sha256(sha256(result).digest()).digest()

    if check != digest[:4]:
        raise ValueError("Invalid checksum")

    return result
