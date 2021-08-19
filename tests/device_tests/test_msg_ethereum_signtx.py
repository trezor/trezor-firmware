# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from trezorlib import ethereum, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

TO_ADDR = "0x1d1c328764a41bda0492b66baa30c4a339ff85ef"


@pytest.mark.altcoin
@pytest.mark.ethereum
class TestMsgEthereumSigntx:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_known_erc20_token(self, client):
        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(data_length=None),
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
            # 200 000 000 in dec, decimals of ADT = 9, trezor1 displays 0.2 ADT, Trezor T 200 000 000 Wei ADT

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                # ADT token address
                to="0xd0d6d6c5fe4a677d343cc433536bb717bae167dd",
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

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_wanchain(self, client):
        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(data_length=None),
                ]
            )
            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/5718350'/0'/0/0"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                # ADT token address
                to="0xd0d6d6c5fe4a677d343cc433536bb717bae167dd",
                chain_id=1,
                tx_type=1,
                # value needs to be 0, token value is set in the contract (data)
                value=100,
            )

            # ad-hoc generated signature. might not be valid.
            assert (
                sig_r.hex()
                == "d6e197029031ec90b53ed14e8233aa78b592400513ac0386d2d55cdedc3d796f"
            )
            assert (
                sig_s.hex()
                == "326e0d600dd1b7ee606eb531b998a6a3b3293d4995fb8cfe0677962e8a43cff6"
            )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_unknown_erc20_token(self, client):
        with client:
            expected_responses = [
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
            ]
            # TT asks for contract address confirmation
            if client.features.model == "T":
                expected_responses.append(
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx)
                )

            expected_responses.append(messages.EthereumTxRequest(data_length=None))
            client.set_expected_responses(expected_responses)

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
                client,
                n=parse_path("44'/60'/0'/0/1"),
                nonce=0,
                gas_price=20,
                gas_limit=20,
                # unknown token address (Grzegorz Brzęczyszczykiewicz Token)
                to="0xfc6b5d6af8a13258f7cbd0d39e11b35e01a32f93",
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

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_nodata(self, client):
        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(data_length=None),  # v,r,s checked later
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/100"),
                chain_id=1,
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=TO_ADDR,
                value=10,
            )

        assert sig_v == 37
        assert (
            sig_r.hex()
            == "364ea282d85ca0e0615ccda301b7b8a56831491284dff36f6738b6110390e154"
        )
        assert (
            sig_s.hex()
            == "361a1771b74ca7136a3aef7624ed0818658dc3700e8ae6a1fbce42c4beb59d91"
        )

        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(data_length=None),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/100"),
                chain_id=1,
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=12345678901234567890,
            )
        assert sig_v == 38
        assert (
            sig_r.hex()
            == "60709d8966ea6c63e4c89cfee847d6fe58a96eb17e6240cb1d7a14b4c3f05915"
        )
        assert (
            sig_s.hex()
            == "4ff112527ec146b493982a4b42def6babccf27facd6f3554d0d26ba18a88e544"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_data(self, client):
        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(data_length=None),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=0,
                gas_price=20,
                gas_limit=20,
                to=TO_ADDR,
                value=10,
                data=b"abcdefghijklmnop" * 16,
            )
        assert sig_v == 37
        assert (
            sig_r.hex()
            == "88ba4067fb0b71fcd9dd840cfe4d040fc545336287882036ea31826232ba5137"
        )
        assert (
            sig_s.hex()
            == "0d855eb6993c2361d58e1789a364567ce97a7df07bb998236500d16af8b3a1a2"
        )

        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=3),
                    messages.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 38
        assert (
            sig_r.hex()
            == "a95a65ef61cafb89ab0e593b2577e3ca23177404b38189375cfc839f0fce9b9e"
        )
        assert (
            sig_s.hex()
            == "45efb6846b33da028b77faf920c5154c5302ee55fe34b75c9b7addb40aac40a9"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_signtx_message(self, client):
        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=3),
                    messages.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to=TO_ADDR,
                value=0,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 38
        assert (
            sig_r.hex()
            == "f1a42daa34cc6ee433fc8329a4b41f8d16967863d1588ae364564bc9e6e9c5f1"
        )
        assert (
            sig_s.hex()
            == "7952c81accea9c9a8d3ed602e7316105fdf7203d6b8a80c4fcfe134a08b15388"
        )

    def test_ethereum_signtx_newcontract(self, client):
        # contract creation without data should fail.
        with pytest.raises(Exception):
            ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=123456,
                gas_price=20000,
                gas_limit=20000,
                to="",
                value=12345678901234567890,
            )

        with client:
            client.set_expected_responses(
                [
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                    messages.EthereumTxRequest(
                        data_length=1024,
                        signature_r=None,
                        signature_s=None,
                        signature_v=None,
                    ),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=1024),
                    messages.EthereumTxRequest(data_length=3),
                    messages.EthereumTxRequest(),
                ]
            )

            sig_v, sig_r, sig_s = ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=0,
                gas_price=20000,
                gas_limit=20000,
                to="",
                value=12345678901234567890,
                data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            )
        assert sig_v == 37
        assert (
            sig_r.hex()
            == "07f6c40dcd3bc875c106304eda9eebb25716c0cf62127478ed22bc24128dbeb7"
        )
        assert (
            sig_s.hex()
            == "7efeedb81b22f2a3f88e7fd3b4119902f09280f4d179eda275b6fdf25e0fdac6"
        )

    def test_ethereum_sanity_checks(self, client):
        # gas overflow
        with pytest.raises(TrezorFailure):
            ethereum.sign_tx(
                client,
                n=parse_path("44'/60'/0'/0/0"),
                chain_id=1,
                nonce=123456,
                gas_price=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
                gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
                to=TO_ADDR,
                value=12345678901234567890,
            )

        # no gas price
        with pytest.raises(TrezorFailure):
            client.call(
                messages.EthereumSignTx(
                    address_n=parse_path("44'/60'/0'/0/0"),
                    chain_id=1,
                    nonce=b"AAA",
                    gas_limit=ethereum.int_to_big_endian(10000),
                    to=TO_ADDR,
                    value=ethereum.int_to_big_endian(12345678901234567890),
                )
            )

        # no gas limit
        with pytest.raises(TrezorFailure):
            client.call(
                messages.EthereumSignTx(
                    address_n=parse_path("44'/60'/0'/0/0"),
                    chain_id=1,
                    nonce=b"AAA",
                    gas_price=ethereum.int_to_big_endian(10000),
                    to=TO_ADDR,
                    value=ethereum.int_to_big_endian(12345678901234567890),
                )
            )

        # no nonce
        # TODO this was supposed to expect a failure if nonce is not provided.
        # Trezor does not raise such failure however.
        # with pytest.raises(TrezorFailure):
        #     client.call(
        #         messages.EthereumSignTx(
        #             address_n=parse_path("44'/60'/0'/0/0"),
        #             gas_price=ethereum.int_to_big_endian(10000),
        #             gas_limit=ethereum.int_to_big_endian(10000),
        #             to=TO_ADDR,
        #             value=ethereum.int_to_big_endian(12345678901234567890),
        #         )
        #     )
