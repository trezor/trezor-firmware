# Copyright (c) 2017 Pieter Wuille
# Copyright (c) 2018 Oskar Hladky
# Copyright (c) 2018 Pavol Rusnak
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from micropython import const

from .bech32 import convertbits

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
ADDRESS_TYPE_P2KH = const(0)
ADDRESS_TYPE_P2SH = const(8)


def cashaddr_polymod(values: list[int]) -> int:
    generator = [
        0x98_F2BC_8E61,
        0x79_B76D_99E2,
        0xF3_3E5F_B3C4,
        0xAE_2EAB_E2A8,
        0x1E_4F43_E470,
    ]
    chk = 1
    for value in values:
        top = chk >> 35
        chk = ((chk & 0x07_FFFF_FFFF) << 5) ^ value
        for i in range(5):
            chk ^= generator[i] if (top & (1 << i)) else 0
    return chk ^ 1


def prefix_expand(prefix: str) -> list[int]:
    return [ord(x) & 0x1F for x in prefix] + [0]


def _calculate_checksum(prefix: str, payload: list[int]) -> list[int]:
    poly = cashaddr_polymod(prefix_expand(prefix) + payload + [0, 0, 0, 0, 0, 0, 0, 0])
    out = []
    for i in range(8):
        out.append((poly >> 5 * (7 - i)) & 0x1F)
    return out


def _b32decode(inputs: str) -> list[int]:
    out = []
    for letter in inputs:
        out.append(CHARSET.find(letter))
    return out


def _b32encode(inputs: list[int]) -> str:
    out = ""
    for char_code in inputs:
        out += CHARSET[char_code]
    return out


def encode(prefix: str, version: int, payload_bytes: bytes) -> str:
    payload_bytes = bytes([version]) + payload_bytes
    payload = convertbits(payload_bytes, 8, 5)
    checksum = _calculate_checksum(prefix, payload)
    return prefix + ":" + _b32encode(payload + checksum)


def decode(prefix: str, addr: str) -> tuple[int, bytes]:
    addr = addr.lower()
    decoded = _b32decode(addr)

    # verify_checksum
    checksum_verified = cashaddr_polymod(prefix_expand(prefix) + decoded) == 0
    if not checksum_verified:
        raise ValueError("Bad cashaddr checksum")

    data = bytes(convertbits(decoded, 5, 8))
    return data[0], data[1:-6]
