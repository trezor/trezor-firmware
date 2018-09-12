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

from trezorlib import messages, tezos
from trezorlib.protobuf import dict_to_proto
from trezorlib.tools import parse_path

from .common import TrezorTest

TEZOS_PATH = parse_path("m/44'/1729'/0'")


@pytest.mark.tezos
@pytest.mark.skip_t1
class TestMsgTezosSignTx(TrezorTest):
    def test_tezos_sign_tx_transaction(self):
        self.setup_mnemonic_allallall()

        resp = tezos.sign_tx(
            self.client,
            TEZOS_PATH,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "f2ae0c72fdd41d7a89bebfe8d6dd6d38e0fcd0782adb8194717176eb70366f64",
                    "transaction": {
                        "source": {
                            "tag": 0,
                            "hash": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        },
                        "fee": 0,
                        "counter": 108925,
                        "gas_limit": 200,
                        "storage_limit": 0,
                        "amount": 10000,
                        "destination": {
                            "tag": 0,
                            "hash": "0004115bce5af2f977acbb900f449c14c53e1d89cf",
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtfmAbUJtZMAJRGMppvDzPtiWBBQiZKf7G15dV9tgkHQefwiV4JeSw5Rj57ZK54FHEthpyzCpfGvAjU8YqhHxMwZP9Z2Jmt"
        )
        assert (
            resp.sig_op_contents.hex()
            == "f2ae0c72fdd41d7a89bebfe8d6dd6d38e0fcd0782adb8194717176eb70366f64080000001e65c88ae6317cd62a638c8abd1e71c83c847500fdd206c80100904e000004115bce5af2f977acbb900f449c14c53e1d89cf003cce7e6dfe3f79a8bd39f77d738fd79140da1a9e762b7d156eca2cf945aae978436cf68c1ec11889e4f2cf074c9642e05b3d65cc2896809af1fbdab0b126f90c"
        )
        assert (
            resp.operation_hash == "opNeGBdgbM5jN2ykz4o8NdsCuJfqNZ6WBEFVbBUmYH8gp45CJvH"
        )

    def test_tezos_sign_reveal_transaction(self):
        self.setup_mnemonic_allallall()

        resp = tezos.sign_tx(
            self.client,
            TEZOS_PATH,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "03cbce9a5ea1fae2566f7f244a01edc5869f5ada9d0bf21c1098017c59be98e0",
                    "reveal": {
                        "source": {
                            "tag": 0,
                            "hash": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        },
                        "fee": 0,
                        "counter": 108923,
                        "gas_limit": 200,
                        "storage_limit": 0,
                        "public_key": "00200da2c0200927dd8168b2b62e1322637521fcefb3184e61c1c3123c7c00bb95",
                    },
                    "transaction": {
                        "source": {
                            "tag": 0,
                            "hash": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        },
                        "fee": 0,
                        "counter": 108924,
                        "gas_limit": 200,
                        "storage_limit": 0,
                        "amount": 10000,
                        "destination": {
                            "tag": 0,
                            "hash": "0004115bce5af2f977acbb900f449c14c53e1d89cf",
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtheQQ78dZM9Sir78T3TNdfnyHrbFw8w3hiGMaLD5mPbGrUiD1jvy5fpsNJW9T5o7qrWBe7y7bai6vZ5KhwJ5HKZ8UnoCbh"
        )
        assert (
            resp.sig_op_contents.hex()
            == "03cbce9a5ea1fae2566f7f244a01edc5869f5ada9d0bf21c1098017c59be98e0070000001e65c88ae6317cd62a638c8abd1e71c83c847500fbd206c8010000200da2c0200927dd8168b2b62e1322637521fcefb3184e61c1c3123c7c00bb95080000001e65c88ae6317cd62a638c8abd1e71c83c847500fcd206c80100904e000004115bce5af2f977acbb900f449c14c53e1d89cf004b33e241c90b828c31cf44a28c123aee3f161049c3cb4c42ec71dd96fbbf8dae9963bdadb33f51d7c6f11ff0e74f0baad742352d980a1899f69c3c65c70fe40f"
        )
        assert (
            resp.operation_hash == "opQHu93L8juNm2VjmsMKioFowWNyMvGzopcuoVcuzFV1bJMhJef"
        )

    def test_tezos_sign_tx_origination(self):
        self.setup_mnemonic_allallall()

        resp = tezos.sign_tx(
            self.client,
            TEZOS_PATH,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "5e556181029c4ce5e54c9ffcbba2fc0966ed4d880ddeb0849bf6387438a7a877",
                    "origination": {
                        "source": {
                            "tag": 0,
                            "hash": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        },
                        "fee": 0,
                        "counter": 108929,
                        "gas_limit": 10000,
                        "storage_limit": 100,
                        "manager_pubkey": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        "balance": 2000000,
                        "spendable": True,
                        "delegatable": True,
                        "delegate": "0049a35041e4be130977d51419208ca1d487cfb2e7",
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigu46YtcVthQQQ2FTcuayNwTcYY1Mpo6BmwCu83qGovi4kHM9CL5h4NaV4NQw8RTEP1VgraR6Kiv5J6RQsDLMzG17V6fcYwp"
        )
        assert (
            resp.sig_op_contents.hex()
            == "5e556181029c4ce5e54c9ffcbba2fc0966ed4d880ddeb0849bf6387438a7a877090000001e65c88ae6317cd62a638c8abd1e71c83c84750081d306904e6400001e65c88ae6317cd62a638c8abd1e71c83c847580897affffff0049a35041e4be130977d51419208ca1d487cfb2e700e785342fd2258277741f93c17c5022ea1be059f47f3e343600e83c50ca191e8318da9e5ec237be9657d0fc6aba654f476c945430239a3c6dfeca21e06be98706"
        )
        assert (
            resp.operation_hash == "onuKkBtP4K2JMGg7YMv7qs869B8aHCEUQecvuiL71aKkY8iPCb6"
        )

    def test_tezos_sign_tx_delegation(self):
        self.setup_mnemonic_allallall()

        resp = tezos.sign_tx(
            self.client,
            TEZOS_PATH,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "9b8b8bc45d611a3ada20ad0f4b6f0bfd72ab395cc52213a57b14d1fb75b37fd0",
                    "delegation": {
                        "source": {
                            "tag": 0,
                            "hash": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        },
                        "fee": 0,
                        "counter": 108927,
                        "gas_limit": 200,
                        "storage_limit": 0,
                        "delegate": "0049a35041e4be130977d51419208ca1d487cfb2e7",
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigu3qGseaB2MghcGQWNWUhPtWgM9rC62FTEVrYWGtzFTHShDxGGmLFfEpJyToRCeRqcgGm3pyXY3NdyATkjmFTtUvJKvb3rX"
        )
        assert (
            resp.sig_op_contents.hex()
            == "9b8b8bc45d611a3ada20ad0f4b6f0bfd72ab395cc52213a57b14d1fb75b37fd00a0000001e65c88ae6317cd62a638c8abd1e71c83c847500ffd206c80100ff0049a35041e4be130977d51419208ca1d487cfb2e7e581d41daf8cab833d5b99151a0303fd04472eb990f7338d7be57afe21c26e779ff4341511694aebd901a0d74d183bbcb726a9be4b873d3b47298f99f2b7e80c"
        )
        assert (
            resp.operation_hash == "oocgc3hyKsGHPsw6WFWJpWT8jBwQLtebQAXF27KNisThkzoj635"
        )
