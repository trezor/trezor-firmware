# This file is part of the Trezor project.
#
# Copyright (C) 2020 SatoshiLabs and contributors
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

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
TXHASH_65b811 = bytes.fromhex(
    "65b811d3eca0fe6915d9f2d77c86c5a7f19bf66b1b1253c2c51cb4ae5f0c017b"
)

PIN = "1234"

pytestmark = pytest.mark.skip_t1


@pytest.mark.setup_client(pin=PIN)
def test_sign_tx(client):
    with client:
        client.use_pin_sequence([PIN])
        btc.authorize_coinjoin(
            client,
            amount=100000000,
            max_fee=50000,
            coordinator="www.example.com",
            n=parse_path("m/84'/1'/0'"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    client.call_raw(messages.LockDevice())

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest(), messages.OwnershipProof()]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.com" + (1).to_bytes(8, "big"),
            preauthorized=True,
        )

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest(), messages.OwnershipProof()]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/5"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.com" + (1).to_bytes(8, "big"),
            preauthorized=True,
        )

    inp1 = messages.TxInputType(
        # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
        # 84'/1'/0'/0/0
        # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
        amount=100000,
        prev_hash=TXHASH_e5b7e2,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        ownership_proof=bytearray.fromhex(
            "534c001900016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100d4ad0374c922848c71d913fba59c81b9075e0d33e884d953f0c4b4806b8ffd0c022024740e6717a2b6a5aa03148c3a28b02c713b4e30fc8aeae67fa69eb20e8ddcd9012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
        ),
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    # Other's coinjoined output.
    out1 = messages.TxOutputType(
        address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )
    # Our coinjoined output.
    out2 = messages.TxOutputType(
        address_n=parse_path("84'/1'/0'/1/1"),
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )
    # Our change output.
    out3 = messages.TxOutputType(
        address_n=parse_path("84'/1'/0'/1/2"),
        amount=7289000 - 50000 - 5 - 5000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )
    # Other's change output.
    out4 = messages.TxOutputType(
        address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
        amount=100000 - 50000 - 5 - 5000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )
    # Coordinator's output.
    out5 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=10,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    with client:
        client.set_expected_responses(
            [
                messages.PreauthorizedRequest(),
                request_input(0),
                request_input(1),
                request_meta(TXHASH_65b811),
                request_input(0, TXHASH_65b811),
                request_output(0, TXHASH_65b811),
                request_output(1, TXHASH_65b811),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(0),
                request_meta(TXHASH_e5b7e2),
                request_input(0, TXHASH_e5b7e2),
                request_output(0, TXHASH_e5b7e2),
                request_output(1, TXHASH_e5b7e2),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2, out3, out4, out5],
            prev_txes=TX_CACHE_TESTNET,
            preauthorized=True,
        )

    assert (
        serialized_tx.hex()
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff0550c3000000000000160014b7a51ede0a66ae36558a3ab097ad86bbd800786150c3000000000000160014167dae080bca35c9ea49c0c8335dcc4b252a1d70cb616e00000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe8c3af0000000000001600142e01768ca46e57210f0bd2c99e630e8168fa5fe50a000000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac00024730440220694105071db8c6c8ba3d385d01694b6f7c17546327ab26d4c53a6503fee301e202202dd310c23a195a6cebc904b91ebd15d782e6dacd08670a72ade2795e7d3ff4ec012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
    )

    # Test unfair mining fee distribution.
    out3.amount = 7289000 - 50000 - 5 - 6000  # Our change output.
    out4.amount = 100000 - 50000 - 5 - 4000  # Other's change output.
    with pytest.raises(TrezorFailure, match="fee over threshold"):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2, out3, out4, out5],
            prev_txes=TX_CACHE_TESTNET,
            preauthorized=True,
        )


def test_wrong_coordinator(client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        amount=100000000,
        max_fee=50000,
        coordinator="www.example.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.org" + (1).to_bytes(8, "big"),
            preauthorized=True,
        )


def test_change_round_id(client):
    # Ensure that if the round ID changes, then GetOwnershipProof fails.

    btc.authorize_coinjoin(
        client,
        amount=100000000,
        max_fee=50000,
        coordinator="www.example.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest(), messages.OwnershipProof()]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.com" + (1).to_bytes(8, "big"),
            preauthorized=True,
        )

    # GetOwnershipProof with changed round ID.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.com" + (2).to_bytes(8, "big"),
            preauthorized=True,
        )
