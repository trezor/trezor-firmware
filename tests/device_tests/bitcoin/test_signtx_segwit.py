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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    forge_prevtx,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API_TESTNET = TxCache("Testnet")

TXHASH_20912f = bytes.fromhex(
    "20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337"
)
TXHASH_338e2d = bytes.fromhex(
    "338e2d02e0eaf8848e38925904e51546cf22e58db5b1860c4a0e72b69c56afe5"
)
TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)


@pytest.mark.parametrize("chunkify", (True, False))
def test_send_p2sh(client: Client, chunkify: bool):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=123_456_789 - 11_000 - 12_300_000,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
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
            client,
            "Testnet",
            [inp1],
            [out1, out2],
            prev_txes=TX_API_TESTNET,
            chunkify=chunkify,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )


def test_send_p2sh_change(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123_456_789 - 11_000 - 12_300_000,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
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
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )


def test_testnet_segwit_big_amount(client: Client):
    # This test is testing transaction with amount bigger than fits to uint32
    address_n = parse_path("m/49h/1h/0h/0/0")
    address = btc.get_address(
        client,
        "Testnet",
        address_n,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    prev_hash, prev_tx = forge_prevtx([(address, 2**32 + 1)], network="testnet")

    inp1 = messages.TxInputType(
        address_n=address_n,
        amount=2**32 + 1,
        prev_hash=prev_hash,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2Mt7P2BAfE922zmfXrdcYTLyR7GUvbwSEns",  # seed allallall, bip32: m/49h/1h/0h/0/1, script type:p2shsegwit
        amount=2**32 + 1,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(prev_hash),
                request_input(0, prev_hash),
                request_output(0, prev_hash),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes={prev_hash: prev_tx}
        )
    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001019e64f9a7d1af8c06e9d04362e6bd6ac1970f8be5321982ad1ce25a65eec3ae5500000000171600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5cffffffff01010000000100000017a914097c569095163e84475d07aa95a1f736df895b7b87024830450221009d87f574f4b73d1f1114b6a053cb4e1e4f223e495bf5ba2c2f9e47eaf3aabb8c022033eaeb7fa07ab9948ed0180ca166e9d3209cc6f598dff7bfc61ea32ad3d995840121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000"
    )


@pytest.mark.multisig
def test_send_multisig_1(client: Client):
    # input: 338e2d02e0eaf8848e38925904e51546cf22e58db5b1860c4a0e72b69c56afe5

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/49h/1h/{i}h"), coin_name="Testnet"
        ).node
        for i in range(1, 4)
    ]
    # address: 2MuqUo9axjz6FfHjSqNMu8kbF1tCjisMrbt
    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[1, 0], signatures=[b"", b"", b""], m=2
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/1h/1/0"),
        prev_hash=TXHASH_338e2d,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address="mu85iAHLpF16VyijB2wn5fcZrjT2bvrhnL",
        amount=100_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    is_core = client.features.model in ("T", "R")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_338e2d),
        request_input(0, TXHASH_338e2d),
        request_output(0, TXHASH_338e2d),
        request_output(1, TXHASH_338e2d),
        request_input(0),
        request_output(0),
        request_input(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        signatures, _ = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
        )

    # store signature
    inp1.multisig.signatures[0] = signatures[0]
    # sign with third key
    inp1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/0d5d04bffd49287d122f509bebd196b1ecba7cbc5f945c28bf8a26dea66e65de",
        tx_hex="01000000000101e5af569cb6720e4a0c86b1b58de522cf4615e5045992388e84f8eae0022d8e330000000023220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7ffffffff01905f0100000000001976a914953e62552a88c235c0691ec74b362a6803a7d93e88ac040047304402203aba48b0a98194a505420633eeca5acd8244061899e0a414f1b0d2de1d721b0f022001b32486e7c443e25cdfdfb14dc183ba31f5329d0078a25f7eb74f7209f347bb014830450221009cbdf84db2585abddf79165340cc0b54037f13bbe5318ec3619d0de680ebbf5d02206a2ef69e154700202ac72330e936c073f8a86cec9443273f4d8739db1019d55a0169522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae00000000",
    )


def test_attack_change_input_address(client: Client):
    # Simulates an attack where the user is coerced into unknowingly
    # transferring funds from one account to another one of their accounts,
    # potentially resulting in privacy issues.

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/49h/1h/12h/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123_456_789 - 11_000 - 12_300_000,
    )

    # Test if the transaction can be signed normally.
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                # The user is required to confirm transfer to another account.
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
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
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
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
        with pytest.raises(TrezorFailure):
            btc.sign_tx(
                client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
            )


def test_attack_mixed_inputs(client: Client):
    TRUE_AMOUNT = 123_456_789
    FAKE_AMOUNT = 120_000_000

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
        sequence=0xFFFFFFFD,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        amount=TRUE_AMOUNT,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        sequence=0xFFFFFFFD,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=31_000_000 + TRUE_AMOUNT - 3_456_789,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    is_core = client.features.model in ("T", "R")
    expected_responses = [
        request_input(0),
        request_input(1),
        request_output(0),
        messages.ButtonRequest(code=messages.ButtonRequestType.ConfirmOutput),
        (
            is_core,
            messages.ButtonRequest(code=messages.ButtonRequestType.ConfirmOutput),
        ),
        (is_core, messages.ButtonRequest(code=messages.ButtonRequestType.SignTx)),
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
            prev_txes=TX_API_TESTNET,
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
            prev_txes=TX_API_TESTNET,
        )

    assert e.value.failure.message.endswith("Invalid amount specified")
