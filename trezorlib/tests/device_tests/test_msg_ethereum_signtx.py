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

from binascii import hexlify, unhexlify

import pytest

from trezorlib import ethereum, messages as proto

from .common import TrezorTest


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
            data.extend(unhexlify("a9059cbb"))
            # 1st function argument (to - the receiver)
            data.extend(
                unhexlify(
                    "000000000000000000000000574bbb36871ba6b78e27f4b4dcfb76ea0091880b"
                )
            )
            # 2nd function argument (value - amount to be transferred)
            data.extend(
                unhexlify(
                    "000000000000000000000000000000000000000000000000000000000bebc200"
                )
            )
            # 200 000 000 in dec, divisibility of ADT = 9, trezor1 displays 0.2 ADT, Trezor T 200 000 000 Wei ADT

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=[0, 0],
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
                hexlify(sig_r)
                == b"75cf48fa173d8ceb68af9e4fb6b78ef69e6ed5e7679ba6f8e3e91d74b2fb0f96"
            )
            assert (
                hexlify(sig_s)
                == b"65de4a8c35263b2cfff3954b12146e8e568aa67a1c2461d6865e74ef75c7e190"
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
            data.extend(unhexlify("a9059cbb"))
            # 1st function argument (to - the receiver)
            data.extend(
                unhexlify(
                    "000000000000000000000000574bbb36871ba6b78e27f4b4dcfb76ea0091880b"
                )
            )
            # 2nd function argument (value - amount to be transferred)
            data.extend(
                unhexlify(
                    "0000000000000000000000000000000000000000000000000000000000000123"
                )
            )
            # since this token is unknown trezor should display "unknown token value"

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=[0, 0],
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
                hexlify(sig_r)
                == b"1707471fbf632e42d18144157aaf4cde101cd9aa9782ad8e30583cfc95ddeef6"
            )
            assert (
                hexlify(sig_s)
                == b"3d2e52ba5904a4bf131abde3f79db826199f5d6f4d241d531d7e8a30a3b9cfd9"
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
                n=[0, 0],
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=10,
            )

        assert sig_v == 27
        assert (
            hexlify(sig_r)
            == b"9b61192a161d056c66cfbbd331edb2d783a0193bd4f65f49ee965f791d898f72"
        )
        assert (
            hexlify(sig_s)
            == b"49c0bbe35131592c6ed5c871ac457feeb16a1493f64237387fab9b83c1a202f7"
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
                n=[0, 0],
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
            )
        assert sig_v == 28
        assert (
            hexlify(sig_r)
            == b"6de597b8ec1b46501e5b159676e132c1aa78a95bd5892ef23560a9867528975a"
        )
        assert (
            hexlify(sig_s)
            == b"6e33c4230b1ecf96a8dbb514b4aec0a6d6ba53f8991c8143f77812aa6daa993f"
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
                n=[0, 0],
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=10,
                data=b"abcdefghijklmnop" * 16,
            )
        assert sig_v == 28
        assert (
            hexlify(sig_r)
            == b"6da89ed8627a491bedc9e0382f37707ac4e5102e25e7a1234cb697cedb7cd2c0"
        )
        assert (
            hexlify(sig_s)
            == b"691f73b145647623e2d115b208a7c3455a6a8a83e3b4db5b9c6d9bc75825038a"
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
                n=[0, 0],
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 28
        assert (
            hexlify(sig_r)
            == b"4e90b13c45c6a9bf4aaad0e5427c3e62d76692b36eb727c78d332441b7400404"
        )
        assert (
            hexlify(sig_s)
            == b"3ff236e7d05f0f9b1ee3d70599bb4200638f28388a8faf6bb36db9e04dc544be"
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
                n=[0, 0],
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=0,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 28
        assert (
            hexlify(sig_r)
            == b"070e9dafda4d9e733fa7b6747a75f8a4916459560efb85e3e73cd39f31aa160d"
        )
        assert (
            hexlify(sig_s)
            == b"7842db33ef15c27049ed52741db41fe3238a6fa3a6a0888fcfb74d6917600e41"
        )

    def test_ethereum_signtx_newcontract(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # contract creation without data should fail.
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
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
                n=[0, 0],
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to="",
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 28
        assert (
            hexlify(sig_r)
            == b"b401884c10ae435a2e792303b5fc257a09f94403b2883ad8c0ac7a7282f5f1f9"
        )
        assert (
            hexlify(sig_s)
            == b"4742fc9e6a5fa8db3db15c2d856914a7f3daab21603a6c1ce9e9927482f8352e"
        )

    def test_ethereum_sanity_checks(self):
        # gas overflow
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                nonce=123456,
                gas_price=0xffffffffffffffffffffffffffffffff,
                gas_limit=0xffffffffffffffffffffffffffffff,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
            )

        # no gas price
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                nonce=123456,
                gas_limit=10000,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
            )

        # no gas limit
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                nonce=123456,
                gas_price=10000,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
            )

        # no nonce
        with pytest.raises(Exception):
            ethereum.sign_tx(
                self.client,
                n=[0, 0],
                gas_price=10000,
                gas_limit=123456,
                to=unhexlify("1d1c328764a41bda0492b66baa30c4a339ff85ef"),
                value=12345678901234567890,
            )
