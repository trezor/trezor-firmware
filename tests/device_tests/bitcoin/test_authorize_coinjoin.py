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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .payment_req import make_payment_request
from .signtx import (
    request_finished,
    request_input,
    request_meta,
    request_output,
    request_payment_req,
)

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
FAKE_TXHASH_f982c0 = bytes.fromhex(
    "f982c0a283bd65a59aa89eded9e48f2a3319cb80361dfab4cf6192a03badb60a"
)

PIN = "1234"
ROUND_ID_LEN = 32

pytestmark = pytest.mark.skip_t1


@pytest.mark.setup_client(pin=PIN)
def test_sign_tx(client: Client):
    # NOTE: FAKE input tx

    commitment_data = b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big")

    with client:
        client.use_pin_sequence([PIN])
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=10_010,
            fee_per_anonymity=5_000_000,  # 0.005 %
            n=parse_path("m/84h/1h/0h"),
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
            parse_path("m/84h/1h/0h/1/0"),
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
            parse_path("m/84h/1h/0h/1/5"),
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
            amount=100_000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100a6c7d59b453efa7b4abc9bc724a94c5655ae986d5924dc29d28bcc2b859cbace022047d2bc4422a47f7b044bd6cdfbf63fe1a0ecbf11393f4c0bf8565f867a5ced16012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=commitment_data,
        ),
        messages.TxInputType(
            address_n=parse_path("m/84h/1h/0h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("m/84h/1h/0h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("m/84h/1h/0h/1/2"),
            amount=7_289_000 - 50_000 - 5 - 5_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100_000 - 50_000 - 5 - 5_000,
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
                request_meta(FAKE_TXHASH_f982c0),
                request_input(0, FAKE_TXHASH_f982c0),
                request_output(0, FAKE_TXHASH_f982c0),
                request_output(1, FAKE_TXHASH_f982c0),
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
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff0ab6ad3ba09261cfb4fa1d3680cb19332a8fe4d9de9ea89aa565bd83a2c082f90100000000ffffffff0550c3000000000000160014b7a51ede0a66ae36558a3ab097ad86bbd800786150c3000000000000160014167dae080bca35c9ea49c0c8335dcc4b252a1d70cb616e00000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe8c3af0000000000001600142e01768ca46e57210f0bd2c99e630e8168fa5fe50a000000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac0002473044022010bcbb2ae63db4bfdfdce298bcf3e302e2b1923d02ff57a2155eaae65fdb2949022026289b6d04d7615bf53b7aa0030b25619c465d639b233297b10d0da9ce1a6ca4012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
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


def test_unfair_fee(client: Client):
    # Test unfair mining fee distribution amongst participants.

    with client:
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=10_000,
            fee_per_anonymity=5_000_000,  # 0.005 %
            n=parse_path("m/84h/1h/0h"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # 84'/1'/0'/0/0
            # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
            amount=100_000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100a6c7d59b453efa7b4abc9bc724a94c5655ae986d5924dc29d28bcc2b859cbace022047d2bc4422a47f7b044bd6cdfbf63fe1a0ecbf11393f4c0bf8565f867a5ced16012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        ),
        messages.TxInputType(
            address_n=parse_path("m/84h/1h/0h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("m/84h/1h/0h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("m/84h/1h/0h/1/2"),
            amount=7_289_000 - 50_000 - 5 - 6_000,  # unfair mining fee
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100_000 - 50_000 - 5 - 4_000,
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


def test_no_anonymity(client: Client):
    # Test CoinJoin transaction giving the user's outputs no gain in anonymity.

    with client:
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_total_fee=5_005,
            fee_per_anonymity=5_000_000,  # 0.005 %
            n=parse_path("m/84h/1h/0h"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDWITNESS,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # 84'/1'/0'/0/0
            # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
            amount=100_000,
            prev_hash=TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
            ownership_proof=bytearray.fromhex(
                "534c001901016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100a6c7d59b453efa7b4abc9bc724a94c5655ae986d5924dc29d28bcc2b859cbace022047d2bc4422a47f7b044bd6cdfbf63fe1a0ecbf11393f4c0bf8565f867a5ced16012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
            ),
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        ),
        messages.TxInputType(
            address_n=parse_path("m/84h/1h/0h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1qk7j3ahs2v6hrv4v282cf0tvxh0vqq7rpt3zcml",
            amount=30_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's coinjoined output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=30_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qze76uzqteg6un6jfcryrxhwvfvjj58ts0swg3d
            address_n=parse_path("m/84h/1h/0h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx
            address_n=parse_path("m/84h/1h/0h/1/2"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1qwn0s88t9r39g72m78mcaxj72sy3ct4m404xsmq
            address_n=parse_path("m/84h/1h/0h/1/3"),
            amount=7_289_000 - 50_000 - 50_000 - 10 - 5_000,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            address="tb1q9cqhdr9ydetjzrct6tyeuccws9505hl96azwxk",
            amount=100_000 - 30_000 - 30_000 - 6 - 5_000,
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


def test_wrong_coordinator(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        max_total_fee=50_000,
        coordinator="www.example.com",
        n=parse_path("m/84h/1h/0h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/84h/1h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_cancel_authorization(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        max_total_fee=50_000,
        coordinator="www.example.com",
        n=parse_path("m/84h/1h/0h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    device.cancel_authorization(client)

    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/84h/1h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_multisession_authorization(client: Client):
    # Authorize CoinJoin with www.example1.com in session 1.
    btc.authorize_coinjoin(
        client,
        max_total_fee=50_000,
        coordinator="www.example1.com",
        n=parse_path("m/84h/1h/0h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    # Open a second session.
    session_id1 = client.session_id
    client.init_device(new_session=True)

    # Authorize CoinJoin with www.example2.com in session 2.
    btc.authorize_coinjoin(
        client,
        max_total_fee=50_000,
        coordinator="www.example2.com",
        n=parse_path("m/84h/1h/0h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    # Requesting a preauthorized ownership proof for www.example1.com should fail in session 2.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/84h/1h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Requesting a preauthorized ownership proof for www.example2.com should succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/84h/1h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101f3ce2cb33599634353452b60b38e311282b6fca743eb6147d3d492066c8963de0002483045022100e09d9c43108841930e5cb0b0336d022684ded53c7b76e2a8e037eab0950f62ae02205409788b59624c75d2af48cd0da4ab2c1814e719b6036baf2df946d9cc68b488012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f"
    )

    # Switch back to the first session.
    session_id2 = client.session_id
    client.init_device(session_id=session_id1)

    # Requesting a preauthorized ownership proof for www.example1.com should succeed in session 1.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/84h/1h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101f3ce2cb33599634353452b60b38e311282b6fca743eb6147d3d492066c8963de000247304402203522d44da76232481ae7f045cddec4a2aa3f3e4e46f7a54ffe456702b6f7185b02203c95860358a703c7497f5e22c9e4506114de5d7257af651ccff1bb6cf50b80cb012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f"
    )

    # Requesting a preauthorized ownership proof for www.example2.com should fail in session 1.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/84h/1h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Cancel the authorization in session 1.
    device.cancel_authorization(client)

    # Requesting a preauthorized ownership proof should fail now.
    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/84h/1h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Switch to the second session.
    client.init_device(session_id=session_id2)

    # Requesting a preauthorized ownership proof for www.example2.com should still succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/84h/1h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )
