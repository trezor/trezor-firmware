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
from trezorlib.tools import parse_path

TO_ADDR = "0x1d1c328764a41bda0492b66baa30c4a339ff85ef"


pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum, pytest.mark.skip_t1]


def test_ethereum_signtx_nodata(client):
    with client:
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "2ceeaabc994fbce2fbd66551f9d48fc711c8db2a12e93779eeddede11e41f636"
    )
    assert (
        sig_s.hex()
        == "2db4a9ecc73da91206f84397ae9287a399076fdc01ed7f3c6554b1c57c39bf8c"
    )


def test_ethereum_signtx_data(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=0,
            gas_limit=20,
            chain_id=1,
            to=TO_ADDR,
            value=10,
            data=b"abcdefghijklmnop" * 16,
            max_gas_fee=20,
            max_priority_fee=1,
        )
    assert sig_v == 0
    assert (
        sig_r.hex()
        == "8e4361e40e76a7cab17e0a982724bbeaf5079cd02d50c20d431ba7dde2404ea4"
    )
    assert (
        sig_s.hex()
        == "411930f091bb508e593e22a9ee45bd4d9eeb504ac398123aec889d5951bdebc3"
    )

    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_limit=20000,
            to=TO_ADDR,
            chain_id=1,
            value=12345678901234567890,
            data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            max_gas_fee=20,
            max_priority_fee=1,
        )
    assert sig_v == 0
    assert (
        sig_r.hex()
        == "2e4f4c0e7c4e51270b891480060712e9d3bcab01e8ad0fadf2dfddd71504ca94"
    )
    assert (
        sig_s.hex()
        == "2599beb32757a144dedc82b79153c21269c9939a9245342bcf35764115b62bc1"
    )


def test_ethereum_signtx_access_list(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
            access_list=[
                messages.EthereumAccessList(
                    address="0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000003"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                    ],
                )
            ],
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "9f8763f3ff8d4d409f6b96bc3f1d84dd504e2c667b162778508478645401f121"
    )
    assert (
        sig_s.hex()
        == "51e30b68b9091cf8138c07380c4378c2711779b68b2e5264d141479f13a12f57"
    )


def test_ethereum_signtx_access_list_larger(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
            access_list=[
                messages.EthereumAccessList(
                    address="0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000003"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                    ],
                ),
                messages.EthereumAccessList(
                    address="0xbb9bc244d798123fde783fcc1c72d3bb8c189413",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000006"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000009"
                        ),
                    ],
                ),
            ],
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "718a3a30827c979975c846d2f60495310c4959ee3adce2d89e0211785725465c"
    )
    assert (
        sig_s.hex()
        == "7d0ea2a28ef5702ca763c1f340427c0020292ffcbb4553dd1c8ea8e2b9126dbc"
    )


def test_ethereum_signtx_known_erc20_token(client):
    with client:

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

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=0,
            max_gas_fee=20,
            max_priority_fee=1,
            gas_limit=20,
            # ADT token address
            to="0xd0d6d6c5fe4a677d343cc433536bb717bae167dd",
            chain_id=1,
            # value needs to be 0, token value is set in the contract (data)
            value=0,
            data=data,
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "94d67bacb7966f881339d91103f5d738d9c491fff4c01a6513c554ab15e86cc0"
    )
    assert (
        sig_s.hex()
        == "405bd19a7bf4ae62d41fcb7844e36c786b106b456185c3d0877a7ce7eab6c751"
    )


def test_ethereum_signtx_unknown_erc20_token(client):
    with client:
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

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/1"),
            nonce=0,
            max_gas_fee=20,
            max_priority_fee=1,
            gas_limit=20,
            # unknown token address (Grzegorz Brzęczyszczykiewicz Token)
            to="0xfc6b5d6af8a13258f7cbd0d39e11b35e01a32f93",
            chain_id=1,
            # value needs to be 0, token value is set in the contract (data)
            value=0,
            data=data,
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "e631b56bcc596844cb8686b2046e36cf33634aa396e7e1ea94a97aac02c18bda"
    )
    assert (
        sig_s.hex()
        == "399bff8752539176c4b2f1d5d2a8f6029f79841d28802149ab339a033ffe4c1f"
    )


def test_ethereum_signtx_large_chainid(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=3125659152,  # Pirl chain id, doesn't support EIP1559 at this time, but chosen for large chain id
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
        )

    assert sig_v == 0
    assert (
        sig_r.hex()
        == "07f8c967227c5a190cb90525c3387691a426fe61f8e0503274280724060ea95c"
    )
    assert (
        sig_s.hex()
        == "0bf83eaf74e24aa9146b23e06f9edec6e25acb81d3830e8d146b9e7b6923ad1e"
    )
