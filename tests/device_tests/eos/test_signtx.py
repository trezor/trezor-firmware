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

from trezorlib import eos
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import EosSignedTx
from trezorlib.tools import parse_path

from ...common import MNEMONIC12

CHAIN_ID = "cf057bbfb72640471fd910bcb67639c22df9f92470936cddc1ade0e2f2e7dc4f"
ADDRESS_N = parse_path("m/44h/194h/0h/0/0")

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.eos,
    pytest.mark.skip_t1,
    pytest.mark.skip_tr,  # coin not supported
    pytest.mark.setup_client(mnemonic=MNEMONIC12),
]


@pytest.mark.parametrize("chunkify", (True, False))
def test_eos_signtx_transfer_token(client: Client, chunkify: bool):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio.token",
                "name": "transfer",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
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

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID, chunkify=chunkify)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JyuCzvv5DUT6bWo2cQ5yjtsbVD3fLbzAbSRhH4wRRfWrivbasrU17VpfK8JqiqiWrw1aqcwYghuqSpwhexRmbHgwx5xib3"
        )


def test_eos_signtx_buyram(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "buyram",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "payer": "miniminimini",
                    "receiver": "miniminimini",
                    "quant": "1000000000.0000 EOS",
                },
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_K86DReCevfV5sfwfM1AYzsT98ZVSYrymsnYz47rXyBBpUSWA8QdkFnQhJQdwJJqJT4vcqYUcoWM2ECUAGJLdKXUn55RymR"
        )


def test_eos_signtx_buyrambytes(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "buyrambytes",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "payer": "miniminimini",
                    "receiver": "miniminimini",
                    "bytes": 1023,
                },
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_Kh4JmjHFQ4HkUP4wMwjoUYuUj3dQYc41P6HXT1YkLD8MSQQjqeCZJXXXAYFeu4xzTyqvowyPpW1N8VsfVw16jt3o1j57pG"
        )


def test_eos_signtx_sellram(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "sellram",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {"account": "miniminimini", "bytes": 1024},
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_Jxcs3V5FNDf7oR8yGCJekVPGR2Bf7LVk3kpr4RFbAg76Y3tSR8DJnDXQRE3j49VjXJSokXBHmGytdtK7V2ycJ64DPZ6LgR"
        )


def test_eos_signtx_delegate(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "delegatebw",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "from": "miniminimini",
                    "receiver": "maximaximaxi",
                    "stake_net_quantity": "1.0000 EOS",
                    "stake_cpu_quantity": "1.0000 EOS",
                    "transfer": True,
                },
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_KdwCsth6XmRG39LxgswkFhJShWdTkTSeg8UDUzJn6qhEES92iGy3P1aJs3HKXNrrUkYU8tJbiXczb2NUJwe4tTnry5CNNH"
        )


def test_eos_signtx_undelegate(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "undelegatebw",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "from": "miniminimini",
                    "receiver": "maximaximaxi",
                    "unstake_net_quantity": "1.0000 EOS",
                    "unstake_cpu_quantity": "1.0000 EOS",
                },
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_KakW1eEPediabKj8YmJq4SqDvtLsKuV1cbuwWj1iAPrG4jt2F2he7xFzgYjgzRHchh2q8Hb9LJoHPevPUWZ5U2HQZWhLXt"
        )


def test_eos_signtx_refund(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "refund",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {"owner": "miniminimini"},
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JwWZSSKQZL1hCdMmwEAKjs3r15kau5gaBrQczKy65QANANzovV6U4XbVUZQkZzaQrNGYAtgxrU1WJ1smWgXZNqtKVQUZqc"
        )


def test_eos_signtx_linkauth(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "linkauth",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
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

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_KVSS3vmu3quh63t2PADN9Fa7tAgEpC8Cg5y1JVQ8MbYUuh5EX4qdCNzgZpjHMBENjbyUiyTNwRDfvA6gM6vWfivTdQHXUd"
        )


def test_eos_signtx_unlinkauth(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "unlinkauth",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "account": "miniminimini",
                    "code": "eosbet",
                    "type": "whatever",
                },
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_K1ioB5KMRC2mmTwYsGwsFU51ENp1XdSBUrb4bxUCLYhoq7Y733WaLZ4Soq9fdrkaJS8uJ3R7Z1ZjyEKRHU8HU4s4MA86zB"
        )


def test_eos_signtx_updateauth(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "updateauth",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
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

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JuNuwmJm7nLfpxbCqXZMxZoU56TzBh8F5PH7ZyPvQMti6QxJbErDGbKCAaHhoRxwWKzv5kj6kX3WyWys6jAzVe9pDhXB1k"
        )


def test_eos_signtx_deleteauth(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "deleteauth",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {"account": "maximaximaxi", "permission": "active"},
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JyDbrnQhvBKx6ZHvrya57ajWtMzWWjy1F2U9NL7cUPer6NJjNFZ6E98qGoyBkQ67VBWKQVW2fWwuG3AeGz7vZ1KkSqRnZb"
        )


def test_eos_signtx_vote(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "voteproducer",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
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

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JxgVhc6ExoTHee3Djrciwmmf2Xck7NLgvAtC2gfgV4Wj2AqMXEb6aKMhpUcTV59VTR1DdnPF1XbiCcJViJiU3zsk1kQz89"
        )


def test_eos_signtx_vote_proxy(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "voteproducer",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {"account": "miniminimini", "proxy": "", "producers": []},
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_KjJzcDg9MT8XbLeP1fgQjdmdE6oNQQisMwbXikqrEZYmJe6GCYg89Wr2donYV6zRfg9h7dJKQDCHugdtsxjtmEdqLtPv25"
        )


def test_eos_signtx_unknown(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "foocontract",
                "name": "baraction",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": "deadbeef",
            }
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JvoJtrHpQJjHAZzEBhiQm75iimYabcAVNDvz8mkempLh6avSJgnXm5JzCCUEBjDtW3syByfXknmgr93Sw3P9RNLnwySmv6"
        )


def test_eos_signtx_newaccount(client: Client):
    transaction = {
        "expiration": "2018-07-14T10:43:28",
        "ref_block_num": 6439,
        "ref_block_prefix": 2995713264,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio",
                "name": "newaccount",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
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
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "payer": "miniminimini",
                    "receiver": "maximaximaxi",
                    "bytes": 4096,
                },
            },
            {
                "account": "eosio",
                "name": "delegatebw",
                "authorization": [{"actor": "miniminimini", "permission": "active"}],
                "data": {
                    "from": "miniminimini",
                    "receiver": "maximaximaxi",
                    "stake_net_quantity": "1.0000 EOS",
                    "stake_cpu_quantity": "1.0000 EOS",
                    "transfer": True,
                },
            },
        ],
        "transaction_extensions": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_JxgTbQsTKAfrJG2LnSAmfUG57MrLshJEeF3BZTPo7FrA1KARGA5gGX4kYctSvpxgb669JC3WfuNQzT8Gm4FkKznTE3sYjb"
        )


def test_eos_signtx_setcontract(client: Client):
    transaction = {
        "expiration": "2018-06-19T13:29:53",
        "ref_block_num": 30587,
        "ref_block_prefix": 338239089,
        "max_net_usage_words": 0,
        "max_cpu_usage_ms": 0,
        "delay_sec": 0,
        "context_free_actions": [],
        "actions": [
            {
                "account": "eosio1",
                "name": "setcode",
                "authorization": [{"actor": "ednazztokens", "permission": "active"}],
                "data": "00" * 1024,
            },
            {
                "account": "eosio1",
                "name": "setabi",
                "authorization": [{"actor": "ednazztokens", "permission": "active"}],
                "data": "00" * 1024,
            },
        ],
        "transaction_extensions": [],
        "context_free_data": [],
    }

    with client:
        resp = eos.sign_tx(client, ADDRESS_N, transaction, CHAIN_ID)
        assert isinstance(resp, EosSignedTx)
        assert (
            resp.signature
            == "SIG_K1_KkRowmmQgKvUxaCWFLUqwP16hPrh7vULMpsFvz5e7ufaGgArKyAWtueWBpdGmy9Ji761UTSA8KfSEJUnccwzh2orPukbgE"
        )
