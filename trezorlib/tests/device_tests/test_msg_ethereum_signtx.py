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

import pytest

from trezorlib import ethereum, messages as proto
from trezorlib.tools import parse_path

from .common import TrezorTest

TO_ADDR = bytes.fromhex("1d1c328764a41bda0492b66baa30c4a339ff85ef")


@pytest.mark.ethereum
class TestMsgEthereumSigntx(TrezorTest):
    def test_ethereum_signtx_known_erc20_token(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(data_length=None),
                ]
            )

            data = bytearray()
            # method id signalizing `transfer(address _to, uint256 _value)` function
            data.extend(bytes.fromhex("a9059cbb"))
            # 1st function argument (to - the receiver)
            data.extend(
                bytes.fromhex(
                    "000000000000000000000000574bbb36871ba6b78e27f4b4dcfb76ea0091880b"
                )
            )
            # 2nd function argument (value - amount to be transferred)
            data.extend(
                bytes.fromhex(
                    "000000000000000000000000000000000000000000000000000000000bebc200"
                )
            )
            # 200 000 000 in dec, divisibility of ADT = 9, trezor1 displays 0.2 ADT, Trezor T 200 000 000 Wei ADT

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                # ADT token address
                to=b"\xd0\xd6\xd6\xc5\xfe\x4a\x67\x7d\x34\x3c\xc4\x33\x53\x6b\xb7\x17\xba\xe1\x67\xdd",
                chain_id=1,
                # value needs to be 0, token value is set in the contract (data)
                value=0,
                data=data,
            )

            # taken from T1 might not be 100% correct but still better than nothing
            assert (
                sig_r.hex()
                == "ec1df922115d256745410fbc2070296756583c8786e4d402a88d4e29ec513fa9"
            )
            assert (
                sig_s.hex()
                == "7001bfe3ba357e4a9f9e0d3a3f8a8962257615a4cf215db93e48b98999fc51b7"
            )

    def test_ethereum_signtx_unknown_erc20_token(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(data_length=None),
                ]
            )

            data = bytearray()
            # method id signalizing `transfer(address _to, uint256 _value)` function
            data.extend(bytes.fromhex("a9059cbb"))
            # 1st function argument (to - the receiver)
            data.extend(
                bytes.fromhex(
                    "000000000000000000000000574bbb36871ba6b78e27f4b4dcfb76ea0091880b"
                )
            )
            # 2nd function argument (value - amount to be transferred)
            data.extend(
                bytes.fromhex(
                    "0000000000000000000000000000000000000000000000000000000000000123"
                )
            )
            # since this token is unknown trezor should display "unknown token value"

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/1"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                # unknown token address (Grzegorz Brzęczyszczykiewicz Token)
                to=b"\xfc\x6b\x5d\x6a\xf8\xa1\x32\x58\xf7\xcb\xd0\xd3\x9e\x11\xb3\x5e\x01\xa3\x2f\x93",
                chain_id=1,
                # value needs to be 0, token value is set in the contract (data)
                value=0,
                data=data,
            )

            # taken from T1 might not be 100% correct but still better than nothing
            assert (
                sig_r.hex()
                == "2559bbf1bcb80992b6eaa96f0074b19606d8ea7bf4219e1c9ac64a12855c0cce"
            )
            assert (
                sig_s.hex()
                == "633a74429eb6d3aeec4ed797542236a85daab3cab15e37736b87a45697541d7a"
            )

    def test_ethereum_signtx_nodata(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(data_length=None),  # v,r,s checked later
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/100"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=TO_ADDR,
                value=10,
            )

        assert sig_v == 27
        assert (
            sig_r.hex()
            == "2f548f63ddb4cf19b6b9f922da58ff71833b967d590f3b4dcc2a70810338a982"
        )
        assert (
            sig_s.hex()
            == "428d35f0dca963b5196b63e7aa5e0405d8bff77d6aee1202183f1f68dacb4483"
        )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(data_length=None),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/100"),
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=12345678901234567890,
            )
        assert sig_v == 27
        assert (
            sig_r.hex()
            == "3bf0470cd7f5ad8d82613199f73deadc55c3c9f32f91b1a21b5ef644144ebd58"
        )
        assert (
            sig_s.hex()
            == "48b3ef1b2502febdf35e9ff4df0ba1fda62f042fad639eb4852a297fc9872ebd"
        )

    def test_ethereum_signtx_data(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(data_length=None),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=TO_ADDR,
                value=10,
                data=b"abcdefghijklmnop" * 16,
            )
        assert sig_v == 27
        assert (
            sig_r.hex()
            == "e90f9e3dbfb34861d40d67570cb369049e675c6eebfdda6b08413a2283421b85"
        )
        assert (
            sig_s.hex()
            == "763912b8801f76cbea7792d98123a245514beeab2f3afebb4bab637888e8393a"
        )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=3),
                    proto.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 27
        assert (
            sig_r.hex()
            == "dd96d82d791118a55601dfcede237760d2e9734b76c373ede5362a447c42ac48"
        )
        assert (
            sig_s.hex()
            == "60a77558f28d483d476f9507cd8a6a4bb47b86611aaff95fd5499b9ee9ebe7ee"
        )

    def test_ethereum_signtx_message(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=3),
                    proto.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=0,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 27
        assert (
            sig_r.hex()
            == "81af16020d3c6ad820cab2e2b0834fa37f4a9b0c2443f151a4e2f12fe1081b09"
        )
        assert (
            sig_s.hex()
            == "7b34b5d8a43771d493cd9fa0c7b27a9563e2a31799fb9f0c2809539a848b9f47"
        )

    def test_ethereum_signtx_newcontract(self):
        self.setup_mnemonic_allallall()

        # contract creation without data should fail.
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to="",
                value=12345678901234567890,
            )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=1024),
                    proto.EthereumTxRequest(data_length=3),
                    proto.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to="",
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 28
        assert (
            sig_r.hex()
            == "c86bda9de238b1c602648996561e7270a3be208da96bbf23474cb8e4014b9f93"
        )
        assert (
            sig_s.hex()
            == "18742403f75a05e7fa9868c30b36f1e55628de02d01c03084c1ff6775a13137c"
        )

    def test_ethereum_sanity_checks(self):
        # gas overflow
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=123456,
                gas_price=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
                gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
                to=TO_ADDR,
                value=12345678901234567890,
            )

        # no gas price
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                nonce=123456,
                gas_limit=10000,
                to=TO_ADDR,
                value=12345678901234567890,
            )

        # no gas limit
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                nonce=123456,
                gas_price=10000,
                to=TO_ADDR,
                value=12345678901234567890,
            )

        # no nonce
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                gas_price=10000,
                gas_limit=123456,
                to=TO_ADDR,
                value=12345678901234567890,
            )
