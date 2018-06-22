# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import hashlib
import struct
from typing import NewType, List

from .coins import slip44

HARDENED_FLAG = 1 << 31

Address = NewType('Address', List[int])


def H_(x: int) -> int:
    """
    Shortcut function that "hardens" a number in a BIP44 path.
    """
    return x | HARDENED_FLAG


def btc_hash(data):
    """
    Double-SHA256 hash as used in BTC
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()


def hash_160_to_bc_address(h160, address_type):
    vh160 = struct.pack('<B', address_type) + h160
    h = btc_hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)


def compress_pubkey(public_key):
    if public_key[0] == 4:
        return bytes((public_key[64] & 1) + 2) + public_key[1:33]
    raise ValueError("Pubkey is already compressed")


def public_key_to_bc_address(public_key, address_type, compress=True):
    if public_key[0] == '\x04' and compress:
        public_key = compress_pubkey(public_key)

    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160, address_type)


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)


def b58encode(v):
    """ encode v, which is a string of bytes, to base58."""

    long_value = 0
    for c in v:
        long_value = long_value * 256 + c

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == 0:
            nPad += 1
        else:
            break

    return (__b58chars[0] * nPad) + result


def b58decode(v, length):
    """ decode v into a string of len bytes."""
    long_value = 0
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base ** i)

    result = b''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = struct.pack('B', mod) + result
        long_value = div
    result = struct.pack('B', long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]:
            nPad += 1
        else:
            break

    result = b'\x00' * nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def parse_path(nstr: str) -> Address:
    """
    Convert BIP32 path string to list of uint32 integers with hardened flags.
    Several conventions are supported to set the hardened flag: -1, 1', 1h

    e.g.: "0/1h/1" -> [0, 0x80000001, 1]

    :param nstr: path string
    :return: list of integers
    """
    if not nstr:
        return []

    n = nstr.split('/')

    # m/a/b/c => a/b/c
    if n[0] == 'm':
        n = n[1:]

    # coin_name/a/b/c => 44'/SLIP44_constant'/a/b/c
    if n[0] in slip44:
        coin_id = slip44[n[0]]
        n[0:1] = ['44h', '{}h'.format(coin_id)]

    def str_to_harden(x: str) -> int:
        if x.startswith('-'):
            return H_(abs(int(x)))
        elif x.endswith(('h', "'")):
            return H_(int(x[:-1]))
        else:
            return int(x)

    try:
        return list(str_to_harden(x) for x in n)
    except Exception:
        raise ValueError('Invalid BIP32 path', nstr)
