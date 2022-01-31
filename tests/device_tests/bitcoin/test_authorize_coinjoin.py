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

from trezorlib import btc, device, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from ..signtx import (
    request_finished,
    request_input,
    request_meta,
    request_output,
    request_payment_req,
)
from .payment_req import make_payment_request

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
ROUND_ID_LEN = 32

pytestmark = pytest.mark.skip_t1


@pytest.mark.setup_client(pin=PIN)
def test_sign_tx(client):
    commitment_data = b"www.example.com" + (1).to_bytes(ROUND_ID_LEN, "big")

    with client:
        client.use_pin_sequence([PIN])
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=10010,
            fee_per_anonymity=5000000,  # 0.005 %
            n=parse_path("m/84'/1'/0'"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    client.call(messages.LockDevice())

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/5"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # 84'/1'/0'/0/0
            # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
            amount=100000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c4000247304402207c7e55f9ad25b03f27e0f51bba5140bafb20d2f29f27dce08e8d0d8d2c4c2efc022060623701649897a8068d5d44efad69e27368e0b5d968daa487139a1367cf2444012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=commitment_data,
        ),
        messages.TxInputType(
            address_n=parse_path("84'/1'/0'/1/0"),
            amount=7289000,
            prev_hash=TXHASH_65b811,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("84'/1'/0'/1/1"),
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("84'/1'/0'/1/2"),
            amount=7289000 - 50000 - 5 - 5000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100000 - 50000 - 5 - 5000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=10,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
    ]

    payment_req = make_payment_request(
        client,
        recipient_name="www.example.com",
        outputs=outputs,
        change_addresses=[
            "tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d",
            "tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx",
        ],
    )
    payment_req.amount = None

    with client:
        client.set_expected_responses(
            [
                messages.PreauthorizedRequest(),
                request_input(0),
                request_input(1),
                request_output(0),
                request_payment_req(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(0),
                request_meta(TXHASH_e5b7e2),
                request_input(0, TXHASH_e5b7e2),
                request_output(0, TXHASH_e5b7e2),
                request_output(1, TXHASH_e5b7e2),
                request_input(1),
                request_meta(TXHASH_65b811),
                request_input(0, TXHASH_65b811),
                request_output(0, TXHASH_65b811),
                request_output(1, TXHASH_65b811),
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
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )

    assert (
        serialized_tx.hex()
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff0550c3000000000000160014b7a51ede0a66ae36558a3ab097ad86bbd800786150c3000000000000160014167dae080bca35c9ea49c0c8335dcc4b252a1d70cb616e00000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe8c3af0000000000001600142e01768ca46e57210f0bd2c99e630e8168fa5fe50a000000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac00024730440220694105071db8c6c8ba3d385d01694b6f7c17546327ab26d4c53a6503fee301e202202dd310c23a195a6cebc904b91ebd15d782e6dacd08670a72ade2795e7d3ff4ec012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
    )

    # Test for a second time.
    btc.sign_tx(
        client,
        "Testnet",
        inputs,
        outputs,
        prev_txes=TX_CACHE_TESTNET,
        payment_reqs=[payment_req],
        preauthorized=True,
    )

    # Test for a third time, fees should exceed max_total_fee.
    with pytest.raises(TrezorFailure, match="Fees exceed authorized limit"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )


def test_unfair_fee(client):
    # Test unfair mining fee distribution amongst participants.

    with client:
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=10000,
            fee_per_anonymity=5000000,  # 0.005 %
            n=parse_path("m/84'/1'/0'"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # 84'/1'/0'/0/0
            # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
            amount=100000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c4000247304402207c7e55f9ad25b03f27e0f51bba5140bafb20d2f29f27dce08e8d0d8d2c4c2efc022060623701649897a8068d5d44efad69e27368e0b5d968daa487139a1367cf2444012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=b"www.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
        ),
        messages.TxInputType(
            address_n=parse_path("84'/1'/0'/1/0"),
            amount=7289000,
            prev_hash=TXHASH_65b811,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("84'/1'/0'/1/1"),
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("84'/1'/0'/1/2"),
            amount=7289000 - 50000 - 5 - 6000,  # unfair mining fee
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100000 - 50000 - 5 - 4000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=10,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
    ]

    payment_req = make_payment_request(
        client,
        recipient_name="www.example.com",
        outputs=outputs,
        change_addresses=[
            "tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d",
            "tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx",
        ],
    )
    payment_req.amount = None

    with pytest.raises(TrezorFailure, match="fee over threshold"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )


def test_no_anonymity(client):
    # Test CoinJoin transaction giving the user's outputs no gain in anonymity.

    with client:
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=5005,
            fee_per_anonymity=5000000,  # 0.005 %
            n=parse_path("m/84'/1'/0'"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # 84'/1'/0'/0/0
            # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
            amount=100000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c4000247304402207c7e55f9ad25b03f27e0f51bba5140bafb20d2f29f27dce08e8d0d8d2c4c2efc022060623701649897a8068d5d44efad69e27368e0b5d968daa487139a1367cf2444012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=b"www.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
        ),
        messages.TxInputType(
            address_n=parse_path("84'/1'/0'/1/0"),
            amount=7289000,
            prev_hash=TXHASH_65b811,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=30000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=30000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("84'/1'/0'/1/1"),
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("84'/1'/0'/1/2"),
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qwn0s88t9r39g72m78mcaxj72sy3ct4m404xsmq
            address_n=parse_path("84'/1'/0'/1/3"),
            amount=7289000 - 50000 - 50000 - 10 - 5000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100000 - 30000 - 30000 - 6 - 5000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=16,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
    ]

    payment_req = make_payment_request(
        client,
        recipient_name="www.example.com",
        outputs=outputs,
        change_addresses=[
            "tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d",
            "tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx",
            "tb1qwn0s88t9r39g72m78mcaxj72sy3ct4m404xsmq",
        ],
    )
    payment_req.amount = None

    with pytest.raises(TrezorFailure, match="No anonymity gain"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )


def test_wrong_coordinator(client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        max_total_fee=50000,
        coordinator="www.example.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_cancel_authorization(client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        max_total_fee=50000,
        coordinator="www.example.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    device.cancel_authorization(client)

    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_multisession_authorization(client):
    # Authorize CoinJoin with www.example1.com in session 1.
    btc.authorize_coinjoin(
        client,
        max_total_fee=50000,
        coordinator="www.example1.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    # Open a second session.
    session_id1 = client.session_id
    client.init_device(new_session=True)

    # Authorize CoinJoin with www.example2.com in session 2.
    btc.authorize_coinjoin(
        client,
        max_total_fee=50000,
        coordinator="www.example2.com",
        n=parse_path("m/84'/1'/0'"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    # Requesting a preauthorized ownership proof for www.example1.com should fail in session 2.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Requesting a preauthorized ownership proof for www.example2.com should succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("84'/1'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101f3ce2cb33599634353452b60b38e311282b6fca743eb6147d3d492066c8963de00024830450221008adf2a7396dc4b73a60930942a29d3452a046310af5ef7d3b6815ad3a2e1666d0220255839c04f6926d85a14aa69fc06e84e85e7e527bc5ce500b6905832ff778828012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f"
    )

    # Switch back to the first session.
    session_id2 = client.session_id
    client.init_device(session_id=session_id1)

    # Requesting a preauthorized ownership proof for www.example1.com should succeed in session 1.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("84'/1'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101f3ce2cb33599634353452b60b38e311282b6fca743eb6147d3d492066c8963de0002483045022100b85411a7c87986b2dc032eb100f4aa7c79102b4aa066c85e86df7de688d04e0f02203cc45917a99f9d1313c51deb5cf8d2930b2308ac22bcf06dbded5872b8538da4012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f"
    )

    # Requesting a preauthorized ownership proof for www.example2.com should fail in session 1.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Cancel the authorization in session 1.
    device.cancel_authorization(client)

    # Requesting a preauthorized ownership proof should fail now.
    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("84'/1'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Switch to the second session.
    client.init_device(session_id=session_id2)

    # Requesting a preauthorized ownership proof for www.example2.com should still succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("84'/1'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )
