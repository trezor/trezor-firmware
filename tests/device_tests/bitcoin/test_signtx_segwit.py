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

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ...tx_cache import TxCache
from ..signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Testnet")

TXHASH_20912f = bytes.fromhex(
    "20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337"
)
TXHASH_9c3192 = bytes.fromhex(
    "9c31922be756c06d02167656465c8dc83bb553bf386a3f478ae65b5c021002be"
)
TXHASH_dee13c = bytes.fromhex(
    "dee13c469e7ab28108a1ce470d74cb40896d9bb459951bdf590ca6a495293a02"
)
TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)


def test_send_p2sh(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123456789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=123456789 - 11000 - 12300000,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )


def test_send_p2sh_change(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123456789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123456789 - 11000 - 12300000,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )


def test_testnet_segwit_big_amount(client):
    # This test is testing transaction with amount bigger than fits to uint32

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49'/1'/0'/0/0"),
        amount=2 ** 32 + 1,
        prev_hash=TXHASH_dee13c,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2Mt7P2BAfE922zmfXrdcYTLyR7GUvbwSEns",  # seed allallall, bip32: m/49'/1'/0'/0/1, script type:p2shsegwit
        amount=2 ** 32 + 1,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_dee13c),
                request_output(0, TXHASH_dee13c),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API
        )
    assert (
        serialized_tx.hex()
        == "01000000000101023a2995a4a60c59df1b9559b49b6d8940cb740d47cea10881b27a9e463ce1de00000000171600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5cffffffff01010000000100000017a914097c569095163e84475d07aa95a1f736df895b7b8702483045022100965aa8897c7cd5f0bff830481ed5259bf662ed0415ab497a6a152a3c335eb0a1022060acbbbada909b6575ac6f19382a6bdf4cab2fa1c5421aa66677806f380ddb870121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000"
    )


@pytest.mark.multisig
def test_send_multisig_1(client):
    nodes = [
        btc.get_public_node(
            client, parse_path(f"49'/1'/{i}'"), coin_name="Testnet"
        ).node
        for i in range(1, 4)
    ]

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[1, 0], signatures=[b"", b"", b""], m=2
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("49'/1'/1'/1/0"),
        prev_hash=TXHASH_9c3192,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=1610436,
    )

    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=1605000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_9c3192),
                request_input(0, TXHASH_9c3192),
                request_output(0, TXHASH_9c3192),
                request_output(1, TXHASH_9c3192),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        signatures, _ = btc.sign_tx(client, "Testnet", [inp1], [out1], prev_txes=TX_API)
        # store signature
        inp1.multisig.signatures[0] = signatures[0]
        # sign with third key
        inp1.address_n[2] = H_(3)
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_9c3192),
                request_input(0, TXHASH_9c3192),
                request_output(0, TXHASH_9c3192),
                request_output(1, TXHASH_9c3192),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "01000000000101be0210025c5be68a473f6a38bf53b53bc88d5c46567616026dc056e72b92319c0100000023220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7ffffffff01887d1800000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac040047304402203fc3fbe6cd6250d82ace4a585debc07587c07d2efc8bb56558c91e1f810fe65402206025bd9a4e80960f617b6e5bfdd568e34aa085d093471b7976e6b14c2a2402a7014730440220327abf491a57964d75c67fad204eb782fa74aa4abde40e5ad30fb0b7696102b7022049e31f2302417be0a87e2f818b93a862a7e67d4178b7cbeee680264f0882113f0169522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae00000000"
    )


def test_attack_change_input_address(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123456789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("49'/1'/12'/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123456789 - 11000 - 12300000,
    )

    # Test if the transaction can be signed normally
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a9142f98413cb83ff8b3eaf1926192e68973cbd68a3a8702473044022013cbce7c575337ca05dbe03b5920a0805b510cd8dfd3180bd7c5d01cec6439cd0220050001be4bcefb585caf973caae0ffec682347f2127cc22f26efd93ee54fd852012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )

    attack_count = 2

    def attack_processor(msg):
        nonlocal attack_count

        if attack_count > 0 and msg.tx.inputs and msg.tx.inputs[0] == inp1:
            attack_count -= 1
            msg.tx.inputs[0].address_n[2] = H_(12)

        return msg

    # Now run the attack, must trigger the exception
    with client:
        client.set_filter(messages.TxAck, attack_processor)
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                request_input(0),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(TrezorFailure) as exc:
            btc.sign_tx(client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API)
        assert exc.value.code == messages.FailureType.ProcessError
        assert exc.value.message.endswith("Transaction has changed during signing")


def test_attack_mixed_inputs(client):
    TRUE_AMOUNT = 123456789
    FAKE_AMOUNT = 120000000

    inp1 = messages.TxInputType(
        address_n=parse_path("44'/1'/0'/0/0"),
        amount=31000000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
        sequence=0xFFFFFFFD,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        amount=TRUE_AMOUNT,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        sequence=0xFFFFFFFD,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=31000000 + TRUE_AMOUNT - 3456789,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    expected_responses = [
        request_input(0),
        request_input(1),
        request_output(0),
        messages.ButtonRequest(code=messages.ButtonRequestType.ConfirmOutput),
        messages.ButtonRequest(code=messages.ButtonRequestType.FeeOverThreshold),
        messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
        request_input(0),
        request_meta(TXHASH_e5040e),
        request_input(0, TXHASH_e5040e),
        request_output(0, TXHASH_e5040e),
        request_output(1, TXHASH_e5040e),
        request_input(1),
        request_meta(TXHASH_20912f),
        request_input(0, TXHASH_20912f),
        request_output(0, TXHASH_20912f),
        request_output(1, TXHASH_20912f),
        request_input(0),
        request_input(1),
        request_output(0),
        request_input(1),
        request_output(0),
        request_input(1),
        request_finished(),
    ]

    if client.features.model == "1":
        # T1 asks for first input for witness again
        expected_responses.insert(-2, request_input(0))

    with client:
        # Sign unmodified transaction.
        # "Fee over threshold" warning is displayed - fee is the whole TRUE_AMOUNT
        client.set_expected_responses(expected_responses)
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_API,
        )

    # In Phase 1 make the user confirm a lower value of the segwit input.
    inp2.amount = FAKE_AMOUNT

    if client.features.model == "1":
        # T1 fails as soon as it encounters the fake amount.
        expected_responses = (
            expected_responses[:4] + expected_responses[5:15] + [messages.Failure()]
        )
    else:
        expected_responses = (
            expected_responses[:4] + expected_responses[5:16] + [messages.Failure()]
        )

    with pytest.raises(TrezorFailure) as e, client:
        client.set_expected_responses(expected_responses)
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_API,
        )

    assert e.value.failure.message.endswith("Invalid amount specified")
