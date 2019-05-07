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

import time

import pytest

from trezorlib import eos
from trezorlib.messages import EosSignedTx
from trezorlib.tools import parse_path

from .common import TrezorTest

CHAIN_ID = "cf057bbfb72640471fd910bcb67639c22df9f92470936cddc1ade0e2f2e7dc4f"
ADDRESS_N = parse_path("m/44'/194'/0'/0/0")


@pytest.mark.skip_t1
@pytest.mark.eos
class TestMsgEosSignTx(TrezorTest):
    def input_flow(self, pages):
        # confirm number of actions
        yield
        self.client.debug.press_yes()

        # swipe through pages
        yield
        for _ in range(pages - 1):
            self.client.debug.swipe_down()
            time.sleep(1)

        # confirm last page
        self.client.debug.press_yes()

    def test_eos_signtx_transfer_token(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio.token",
                    "name": "transfer",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "from": "miniminimini",
                        "to": "maximaximaxi",
                        "quantity": "1.0000 EOS",
                        "memo": "testtest",
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=3))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "0a9a0f467697010b743ffd02eae6698464c8b5c84b696245397287c225f85e01"
            )
            assert (
                resp.signature_s.hex()
                == "3ec6a0175e5209be6789587a9d6b5f61593b841a751112faa05d9efdd9239d40"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_buyram(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "buyram",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "payer": "miniminimini",
                        "receiver": "miniminimini",
                        "quant": "1000000000.0000 EOS",
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "480bdc505ba196d445d92ea12bda9d39f986d01620efcffe98bcf645ddcbb4ec"
            )
            assert (
                resp.signature_s.hex()
                == "35c8e2105f0228c9e1e511682ae79eac1b7b90bc84c1a0dae13245b7f0f96abf"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_buyrambytes(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "buyrambytes",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "payer": "miniminimini",
                        "receiver": "miniminimini",
                        "bytes": 1023,
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "52267ee5f3ff73939af5ccdaa3406e0783deaf76accf5ce4ceb9714cdbdf7d6b"
            )
            assert (
                resp.signature_s.hex()
                == "53aa9a9ecf044396441a559b51d3b97e239321c895823aad6888b0de2063a078"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_sellram(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "sellram",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {"account": "miniminimini", "bytes": 1024},
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "04c0fdf1d2e0ea21af292173eacc2c7db90f7764abe69b79a8c2b24201af27c4"
            )
            assert (
                resp.signature_s.hex()
                == "7bb29f12eaaabbebdb5190d30367012a80128138b5024b30e93e3afb3d24734e"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_delegate(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "delegatebw",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "sender": "miniminimini",
                        "receiver": "maximaximaxi",
                        "stake_net_quantity": "1.0000 EOS",
                        "stake_cpu_quantity": "1.0000 EOS",
                        "transfer": True,
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=3))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "03b4ccb74b7ad54f28fdeda244facb3038cf70424fd6aa4b171a3bb02a591504"
            )
            assert (
                resp.signature_s.hex()
                == "4e24e08d1789421e17ba47e0e4635a3721400a795e40a8896dc5e5af4a95343d"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_undelegate(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "undelegatebw",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "sender": "miniminimini",
                        "receiver": "maximaximaxi",
                        "unstake_net_quantity": "1.0000 EOS",
                        "unstake_cpu_quantity": "1.0000 EOS",
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "3f39722a88f12395f3cfcdbe218c185f02295ec07a5da8f4b953d5ec3c9ec36b"
            )
            assert (
                resp.signature_s.hex()
                == "7acbae47d60cd538ca28fcc8f3dae8f03b3812e7719dd4e9c069a66dbac5ebf3"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_refund(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "refund",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {"owner": "miniminimini"},
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "113c4867f77c371ff4701beb794ff0a0a6a1137a0115d0f4b5245c391e9f596f"
            )
            assert (
                resp.signature_s.hex()
                == "27203aaaeb8cdbc92c0af32f840c385ac6202e3b4e927bda59d397ebef513381"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_linkauth(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "linkauth",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "account": "maximaximaxi",
                        "code": "eosbet",
                        "type": "whatever",
                        "requirement": "active",
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "5c9bf154dc77649ccf5a997441fcd4041e9da79149078df27a1c6268cf237c75"
            )
            assert (
                resp.signature_s.hex()
                == "3e432ddcd17feb2997145d11240b0ca4344a01e2d96e9886533bca7ffceb10cd"
            )
            assert resp.signature_v == 32

    def test_eos_signtx_unlinkauth(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "unlinkauth",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "account": "miniminimini",
                        "code": "eosbet",
                        "type": "whatever",
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "316c296594fd7a4dd3b615d80c630fda256e9a3460b00d4f16eede1fb2af9574"
            )
            assert (
                resp.signature_s.hex()
                == "76d023913b4f323cfa857d144bf78a4d561954bb23c5df9a31649c9503c3a3b7"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_updateauth(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "updateauth",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "account": "miniminimini",
                        "permission": "active",
                        "parent": "owner",
                        "auth": {
                            "threshold": 1,
                            "keys": [
                                {
                                    "key": "EOS8Dkj827FpinZBGmhTM28B85H9eXiFH5XzvLoeukCJV5sKfLc6K",
                                    "weight": 1,
                                },
                                {
                                    "key": "EOS8Dkj827FpinZBGmhTM28B85H9eXiFH5XzvLoeukCJV5sKfLc6K",
                                    "weight": 2,
                                },
                            ],
                            "accounts": [
                                {
                                    "permission": {
                                        "actor": "miniminimini",
                                        "permission": "active",
                                    },
                                    "weight": 3,
                                }
                            ],
                            "waits": [{"wait_sec": 55, "weight": 4}],
                        },
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=8))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "00f0ca8ffa8208e72df509a3b356e77056b234d4db167b58d485f30cb9c61841"
            )
            assert (
                resp.signature_s.hex()
                == "3f6fb40ffa4e1cf6f3bcb0d8fa3873a2b5a05384ca9251159968558688a4e43d"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_deleteauth(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "deleteauth",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {"account": "maximaximaxi", "permission": "active"},
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "6fe7d66f8be2fe3de23c48561e8a17113d1a0aabcf0d4160e9bd8af90f5a608f"
            )
            assert (
                resp.signature_s.hex()
                == "3cec8db96be2f6aa7bb00302cec6ad3c8655b492f9a2b84b3c61df6bc81f0d83"
            )
            assert resp.signature_v == 32

    def test_eos_signtx_vote(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "voteproducer",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "account": "miniminimini",
                        "proxy": "",
                        "producers": [
                            "argentinaeos",
                            "bitfinexeos1",
                            "cryptolions1",
                            "eos42freedom",
                            "eosamsterdam",
                            "eosasia11111",
                            "eosauthority",
                            "eosbeijingbp",
                            "eosbixinboot",
                            "eoscafeblock",
                            "eoscanadacom",
                            "eoscannonchn",
                            "eoscleanerbp",
                            "eosdacserver",
                            "eosfishrocks",
                            "eosflytomars",
                            "eoshuobipool",
                            "eosisgravity",
                            "eoslaomaocom",
                            "eosliquideos",
                            "eosnewyorkio",
                            "eosriobrazil",
                            "eosswedenorg",
                            "eostribeprod",
                            "helloeoscnbp",
                            "jedaaaaaaaaa",
                            "libertyblock",
                            "starteosiobp",
                            "teamgreymass",
                        ],
                    },
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=6))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "1a303dcb27d2d17bc9efc89b10c41d9d78f7e3d671e3475bb1115b988f918770"
            )
            assert (
                resp.signature_s.hex()
                == "07869385bf3af8cf0a4ee9daf4f8dd122650c7d59da48d6d9ce1e26b59753324"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_vote_proxy(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "voteproducer",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {"account": "miniminimini", "proxy": "", "producers": []},
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "6f511059a910d256ac20483bfedef2ada3b2d04f3261c97c0fce9455ca8b7ef4"
            )
            assert (
                resp.signature_s.hex()
                == "58d795deaf5c9b686e5bcaeabee801ad78e6675f051c24972d8c47abd33585f0"
            )
            assert resp.signature_v == 32

    def test_eos_signtx_unknown(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "foocontract",
                    "name": "baraction",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": "deadbeef",
                }
            ],
            "transaction_extensions": [],
        }

        with self.client:
            self.client.set_input_flow(self.input_flow(pages=2))
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "0bcc986299cf4eb1d5e5bc73620972b2b6683cd4230953a6f1725017927fd9ba"
            )
            assert (
                resp.signature_s.hex()
                == "488f7830e30eea5c7b4a96156bf7ffb0983c45a96211ca070b9db3bc6ba4db02"
            )
            assert resp.signature_v == 31

    def test_eos_signtx_newaccount(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-07-14T10:43:28",
            "ref_block_num": 6439,
            "ref_block_prefix": 2995713264,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio",
                    "name": "newaccount",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "creator": "miniminimini",
                        "name": "maximaximaxi",
                        "owner": {
                            "threshold": 1,
                            "keys": [
                                {
                                    "key": "EOS8Dkj827FpinZBGmhTM28B85H9eXiFH5XzvLoeukCJV5sKfLc6K",
                                    "weight": 1,
                                }
                            ],
                            "accounts": [],
                            "waits": [],
                        },
                        "active": {
                            "threshold": 1,
                            "keys": [
                                {
                                    "key": "EOS8Dkj827FpinZBGmhTM28B85H9eXiFH5XzvLoeukCJV5sKfLc6K",
                                    "weight": 1,
                                }
                            ],
                            "accounts": [],
                            "waits": [],
                        },
                    },
                },
                {
                    "account": "eosio",
                    "name": "buyrambytes",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "payer": "miniminimini",
                        "receiver": "maximaximaxi",
                        "bytes": 4096,
                    },
                },
                {
                    "account": "eosio",
                    "name": "delegatebw",
                    "authorization": [
                        {"actor": "miniminimini", "permission": "active"}
                    ],
                    "data": {
                        "sender": "miniminimini",
                        "receiver": "maximaximaxi",
                        "stake_net_quantity": "1.0000 EOS",
                        "stake_cpu_quantity": "1.0000 EOS",
                        "transfer": True,
                    },
                },
            ],
            "transaction_extensions": [],
        }

        def input_flow():
            # confirm number of actions
            yield
            self.client.debug.press_yes()

            # swipe through new account
            yield
            for _ in range(5):
                self.client.debug.swipe_down()
                time.sleep(1)

            # confirm new account
            self.client.debug.press_yes()

            # swipe through buyrambytes
            yield
            self.client.debug.swipe_down()
            time.sleep(1)

            # confirm buyrambytes
            self.client.debug.press_yes()

            # swipe through delegatebw
            yield
            for _ in range(2):
                self.client.debug.swipe_down()
                time.sleep(1)

            # confirm delegatebw
            self.client.debug.press_yes()

        with self.client:
            self.client.set_input_flow(input_flow)
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "6346a807eef0257a34269b034df7470e134261833d0da5fe0bd91aedf5a47f86"
            )
            assert (
                resp.signature_s.hex()
                == "676a1fcd0d8faff63ec206c8596de9cb5d35037d05f337afdc22c7b9e0863e77"
            )
            assert resp.signature_v == 32

    def test_eos_signtx_setcontract(self):
        self.setup_mnemonic_nopin_nopassphrase()
        transaction = {
            "expiration": "2018-06-19T13:29:53",
            "ref_block_num": 30587,
            "ref_block_prefix": 338239089,
            "net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [
                {
                    "account": "eosio1",
                    "name": "setcode",
                    "authorization": [
                        {"actor": "ednazztokens", "permission": "active"}
                    ],
                    "data": "00" * 1024,
                },
                {
                    "account": "eosio1",
                    "name": "setabi",
                    "authorization": [
                        {"actor": "ednazztokens", "permission": "active"}
                    ],
                    "data": "00" * 1024,
                },
            ],
            "transaction_extensions": [],
            "context_free_data": [],
        }

        def input_flow():
            # confirm number of actions
            yield
            self.client.debug.press_yes()

            # swipe through setcode
            yield
            self.client.debug.swipe_down()
            time.sleep(1)

            # confirm setcode
            self.client.debug.press_yes()

            # swipe through setabi
            yield
            self.client.debug.swipe_down()
            time.sleep(1)

            # confirm setabi
            self.client.debug.press_yes()

        with self.client:
            self.client.set_input_flow(input_flow)
            resp = eos.sign_tx(self.client, ADDRESS_N, transaction, CHAIN_ID)

            assert isinstance(resp, EosSignedTx)
            assert (
                resp.signature_r.hex()
                == "674bbe7c8c7b9abf03ab38851cb53411e794afff04737895962643b1ed94b7d1"
            )
            assert (
                resp.signature_s.hex()
                == "1e47559db68d435494e832a16cc08ae7a67b533013ab3407f7a89d5e28de98b7"
            )
            assert resp.signature_v == 32
