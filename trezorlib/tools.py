# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016      Jochen Hoenicke <hoenicke@gmail.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
import binascii
import struct
import sys

if sys.version_info < (3,):
    def byteindex(data, index):
        return ord(data[index])
    def iterbytes(data):
        return (ord (char) for char in data)
else:
    byteindex = lambda data, index: data[index]
    iterbytes = iter

Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()

def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()


def hash_160_to_bc_address(h160, address_type):
    vh160 = struct.pack('<B', address_type) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def compress_pubkey(public_key):
    if byteindex(public_key, 0) == 4:
        return bytes((byteindex(public_key, 64) & 1) + 2) + public_key[1:33]
    raise Exception("Pubkey is already compressed")

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
    for c in iterbytes(v):
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
    for c in iterbytes(v):
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

def monkeypatch_google_protobuf_text_format():
    # monkeypatching: text formatting of protobuf messages
    import google.protobuf.text_format
    import google.protobuf.descriptor

    _oldPrintFieldValue = google.protobuf.text_format.PrintFieldValue

    def _customPrintFieldValue(field, value, out, indent=0, as_utf8=False, as_one_line=False, pointy_brackets=False, float_format=None):
        if field.type == google.protobuf.descriptor.FieldDescriptor.TYPE_BYTES:
            _oldPrintFieldValue(field, 'hex(%s)' % binascii.hexlify(value), out, indent, as_utf8, as_one_line)
        else:
            _oldPrintFieldValue(field, value, out, indent, as_utf8, as_one_line)

    google.protobuf.text_format.PrintFieldValue = _customPrintFieldValue

