# Copyright (c) 2017 Pieter Wuille
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


"""Reference tests for cashaddr adresses"""

from common import *
from trezor.crypto import base58, cashaddr


VALID_CHECKSUM = [
    "prefix:x64nx6hz",
    "p:gpf8m4h7",
    "bitcoincash:qpzry9x8gf2tvdw0s3jn54khce6mua7lcw20ayyn",
    "bchtest:testnetaddress4d6njnut",
    "bchreg:555555555555555555555555555555555555555555555udxmlmrz",
]

VALID_ADDRESS = [
    ("1BpEi6DfDAUFd7GtittLSdBeYJvcoaVggu", "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a"),
    ("1KXrWXciRDZUpQwQmuM1DbwsKDLYAYsVLR", "bitcoincash:qr95sy3j9xwd2ap32xkykttr4cvcu7as4y0qverfuy"),
    ("16w1D5WRVKJuZUsSRzdLp9w3YGcgoxDXb", "bitcoincash:qqq3728yw0y47sqn6l2na30mcw6zm78dzqre909m2r"),
    ("3CWFddi6m4ndiGyKqzYvsFYagqDLPVMTzC", "bitcoincash:ppm2qsznhks23z7629mms6s4cwef74vcwvn0h829pq"),
    ("3LDsS579y7sruadqu11beEJoTjdFiFCdX4", "bitcoincash:pr95sy3j9xwd2ap32xkykttr4cvcu7as4yc93ky28e"),
    ("31nwvkZwyPdgzjBJZXfDmSWsC4ZLKpYyUw", "bitcoincash:pqq3728yw0y47sqn6l2na30mcw6zm78dzq5ucqzc37")
]


class TestCryptoCashAddr(unittest.TestCase):

    def test_valid_checksum(self):
        for test in VALID_CHECKSUM:
            prefix, addr = test.split(':')
            cashaddr.decode(prefix, addr)

    def test_invalid_checksum(self):
        for test in VALID_CHECKSUM:
            test += 'xxx'
            prefix, addr = test.split(':')
            with self.assertRaises(ValueError):
                cashaddr.decode(prefix, addr)

    def test_valid_address(self):
        # b58 -> cashaddr
        for b58, ca in VALID_ADDRESS:
            data = base58.decode_check(b58)
            version = data[0]
            if version == 5:
                version = 8
            enc = cashaddr.encode('bitcoincash', version, data[1:])
            self.assertEqual(ca, enc)
        # cashaddr -> base58
        for b58, ca in VALID_ADDRESS:
            prefix, addr = ca.split(':')
            version, data = cashaddr.decode(prefix, addr)
            if version == 8:
                version = 5
            enc = base58.encode_check(bytes([version]) + data)
            self.assertEqual(b58, enc)


if __name__ == "__main__":
    unittest.main()
