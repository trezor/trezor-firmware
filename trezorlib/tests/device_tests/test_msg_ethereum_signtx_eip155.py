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

from binascii import unhexlify, hexlify
import pytest

from .common import TrezorTest
from trezorlib import messages as proto


@pytest.mark.ethereum
class TestMsgEthereumSigntxChainId(TrezorTest):
    def test_ethereum_signtx_eip155(self):

        # chain_id, nonce, sig_v, sig_r, sig_s, value, gas_limit, data
        VECTORS = [
            (
                3,
                0,
                41,
                b"a90d0bc4f8d63be69453dd62f2bb5fff53c610000abf956672564d8a654d401a",
                b"544a2e57bc8b4da18660a1e6036967ea581cc635f5137e3ba97a750867c27cf2",
                100000000000000000,
                21000,
                None,
            ),
            (
                3,
                1,
                42,
                b"699428a6950e23c6843f1bf3754f847e64e047e829978df80d55187d19a401ce",
                b"087343d0a3a2f10842218ffccb146b59a8431b6245ab389fde22dc833f171e6e",
                100000000000000000,
                21000,
                None,
            ),
            (
                3,
                2,
                42,
                b"ba85b622a8bb82606ba96c132e81fa8058172192d15bc41d7e57c031bca17df4",
                b"6473b75997634b6f692f8d672193591d299d5bf1c2d6e51f1a14ed0530b91c7d",
                100000000000000000,
                21004,
                b"\0",
            ),
            (
                3,
                3,
                42,
                b"d021c98f92859c8db5e4de2f0e410a8deb0c977eb1a631e323ebf7484bd0d79a",
                b"2c0e9defc9b1e895dc9520ff25ba3c635b14ad70aa86a5ad6c0a3acb82b569b6",
                100000000000000000,
                299732,
                b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            ),
            (
                3,
                4,
                42,
                b"dd52f026972a83c56b7dea356836fcfc70a68e3b879cdc8ef2bb5fea23e0a7aa",
                b"079285fe579c9a2da25c811b1c5c0a74cd19b6301ee42cf20ef7b3b1353f7242",
                0,
                21004,
                b"\0",
            ),
            (
                1,
                1,
                37,
                b"bae6198fdc87ccad6256e543617a34d052bfd17ae3be0bec7fbf8ea34bf9c930",
                b"7d12f625f3e54700b6ed14ab669f45a8a2b5552c39f0781b0ab3796f19e6b4d1",
                0,
                21004,
                b"\0",
            ),
            (
                255,
                1,
                546,
                b"7597a40719509ae3850d2eba808b7b2f7d272fda316e1321e5ebcc911e9f1b0d",
                b"269dd69248273820f65b43d8824bb7aff1aa4e35ee663a5433a5df8f0c47dc31",
                0,
                21004,
                b"\0",
            ),
            (
                256,
                1,
                547,
                b"64e9821db2001ff5dff13c9d8c7fb0701ff860f5f95155d378fb9fcc06088f28",
                b"4d03f339afed717e2155f044a6b0a895b5ac98343f1745e7525870c2046c36bc",
                0,
                21004,
                b"\0",
            ),
            (
                65535,
                1,
                131106,
                b"6f2275808dc328184d7aa019d0a68f8dd8234969576a477670934145bb358969",
                b"2be1ff9045bccff9ba3d6d5c7789a52c52c9679526dd3ec349caa318c3d055ff",
                0,
                21004,
                b"\0",
            ),
            (
                65536,
                1,
                131107,
                b"e16e35afe534a46e3e4cf09f355cbf02edc01937c2b444238162c2aca79037b8",
                b"1083b84e21b1cbad95c7ea9792818c18fa716aa25951c5341b48732d611a396a",
                0,
                21004,
                b"\0",
            ),
            (
                16777215,
                1,
                33554466,
                b"f9753ee68cf2af20638cc753945d157039504f82d6d6fe0ec98806b64366c551",
                b"056b57a69d88a4b71fba993c580d8bbf04f2c857f97a8b7d4b2892b5dafa9114",
                0,
                21004,
                b"\0",
            ),
            (
                16777216,
                1,
                33554468,
                b"23a5399650c6efa46a25a0a966a29119830d9c587b6b93da43cb0be6d3c69059",
                b"5a6eddffc62317a6a3801608071655a9c43423aef9705b2f5df4212942265c37",
                0,
                21004,
                b"\0",
            ),
            (
                2147483629,
                1,
                4294967294,
                b"6a996586f1ea19afe9cb0ca44dec6bb8643cdf53b5cf148323c94a32a04b087d",
                b"0d086b208df6826657edf98010972b2649b323466a7ea4b67e7285fb9e829481",
                0,
                21004,
                b"\0",
            ),
        ]

        self.setup_mnemonic_allallall()

        for ci, n, sv, sr, ss, v, gl, d in VECTORS:
            sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
                n=[0x80000000 | 44, 0x80000000 | 1, 0x80000000, 0, 0],
                nonce=n,
                gas_price=20000000000,
                gas_limit=gl,
                to=unhexlify("8ea7a3fccc211ed48b763b4164884ddbcf3b0a98"),
                value=v,
                chain_id=ci,
                data=d,
            )
            assert sig_v == sv
            assert hexlify(sig_r) == sr
            assert hexlify(sig_s) == ss
