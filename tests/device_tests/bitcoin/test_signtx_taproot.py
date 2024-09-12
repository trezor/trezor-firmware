# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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

from trezorlib import btc, messages, models
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ...bip32 import deserialize
from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings
from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Testnet")

TXHASH_7956f1 = bytes.fromhex(
    "7956f1de3e7362b04115b64a31f0b6822c50dd6c08d78398f392a0ac3f0e357b"
)
TXHASH_3ac32e = bytes.fromhex(
    "3ac32e90831d79385eee49d6030a2123cd9d009fe8ffc3d470af9a6a777a119b"
)
TXHASH_df862e = bytes.fromhex(
    "df862e31da31ff84addd392f6aa89af18978a398ea258e4901ae72894b66679f"
)
TXHASH_8c3ea7 = bytes.fromhex(
    "8c3ea7a10ab6d289119b722ec8c27b70c17c722334ced31a0370d782e4b6775d"
)
TXHASH_901593 = bytes.fromhex(
    "901593bed347678d9762fdee728c35dc4ec3cfdc3728a4d72dcaab3751122e85"
)
TXHASH_091446 = bytes.fromhex(
    "09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a"
)
TXHASH_65b811 = bytes.fromhex(
    "65b811d3eca0fe6915d9f2d77c86c5a7f19bf66b1b1253c2c51cb4ae5f0c017b"
)
TXHASH_ec5194 = bytes.fromhex(
    "ec519494bea3746bd5fbdd7a15dac5049a873fa674c67e596d46505b9b835425"
)
TXHASH_c96621 = bytes.fromhex(
    "c96621a96668f7dd505c4deb9ee2b2038503a5daa4888242560e9b640cca8819"
)
TXHASH_e56e8b = bytes.fromhex(
    "e56e8bdb23625856c54f5f52e3edc10ebabd72c839eed41a49f8ec2ea3691363"
)
TXHASH_b84fd2 = bytes.fromhex(
    "b84fd297347318ff6693513637b11005600f93f4af60a44ffebaea1b5637d06c"
)
TXHASH_bedf7b = bytes.fromhex(
    "bedf7b99c7e8e92f64d233c3789ba265671b89b1ab048296243a27da872f6494"
)
TXHASH_d20c2e = bytes.fromhex(
    "d20c2e9f00220048a20e9a7240a9f41d57ca29541009d3477316233416946145"
)


@pytest.mark.parametrize("chunkify", (True, False))
def test_send_p2tr(client: Client, chunkify: bool):
    inp1 = messages.TxInputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("m/86h/1h/0h/1/0"),
        amount=4_600,
        prev_hash=TXHASH_ec5194,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        # 86'/1'/1'/0/0
        address="tb1paxhjl357yzctuf3fe58fcdx6nul026hhh6kyldpfsf3tckj9a3wslqd7zd",
        amount=4_450,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API, chunkify=chunkify
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/6dfac2f0d66e1972fea2bca80b6d6db80f6f48deacfdef42f15ff9625acdca59",
        tx_hex="010000000001012554839b5b50466d597ec674a63f879a04c5da157addfbd56b74a3be949451ec0000000000ffffffff016211000000000000225120e9af2fc69e20b0be2629cd0e9c34da9f3ef56af7beac4fb4298262bc5a45ec5d0140aacd291b886f40025e93236f69653423b0c50912fbe43aacced10f2690cfc4872fb37694a947e893389084577ffce3c214b09ff4801006b1e7542ee23719abd100000000",
    )


def test_send_two_with_change(client: Client):
    inp1 = messages.TxInputType(
        # tb1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq8s8a5u
        address_n=parse_path("m/86h/1h/0h/0/0"),
        amount=6_800,
        prev_hash=TXHASH_c96621,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    inp2 = messages.TxInputType(
        # tb1p8tvmvsvhsee73rhym86wt435qrqm92psfsyhy6a3n5gw455znnpqm8wald
        address_n=parse_path("m/86h/1h/0h/0/1"),
        amount=13_000,
        prev_hash=TXHASH_c96621,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        # 84'/1'/1'/0/0
        address="tb1q7r9yvcdgcl6wmtta58yxf29a8kc96jkyxl7y88",
        amount=15_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("m/86h/1h/0h/1/0"),
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
        amount=6_800 + 13_000 - 200 - 15_000,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_API
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/1054eb649110534518239bca2abebebee76d50addac27d0d582cef2b9b9d80c0",
        tx_hex="010000000001021988ca0c649b0e56428288a4daa5038503b2e29eeb4d5c50ddf76866a92166c90000000000ffffffff1988ca0c649b0e56428288a4daa5038503b2e29eeb4d5c50ddf76866a92166c90100000000ffffffff02983a000000000000160014f0ca4661a8c7f4edad7da1c864a8bd3db05d4ac4f8110000000000002251209a9af24b396f593b34e23fefba6b417a55c5ee3f430c3837379fcb5246ab36d70140aad93b4abfdc18826a60d79dc648c58810d56c24273f02dde4ac614367395feec25e809c0fdb58fb31f5631ef798a95d82864efc2b0a48b1be83196193ece05401402624067d8ef3705b908956fa824d36998a1522b3f01f38272c11ad5488fb63cb6d7c68d82e8e2d052805610bce34048335ed9c15037ef36b6e2accc0d3f5893500000000",
    )


def test_send_mixed(client: Client):
    inp1 = messages.TxInputType(
        # 2MutHjgAXkqo3jxX2DZWorLAckAnwTxSM9V
        address_n=parse_path("m/49h/1h/1h/0/0"),
        amount=20_000,
        prev_hash=TXHASH_8c3ea7,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    inp2 = messages.TxInputType(
        # tb1q7r9yvcdgcl6wmtta58yxf29a8kc96jkyxl7y88
        address_n=parse_path("m/84h/1h/1h/0/0"),
        amount=15_000,
        prev_hash=TXHASH_7956f1,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp3 = messages.TxInputType(
        # tb1paxhjl357yzctuf3fe58fcdx6nul026hhh6kyldpfsf3tckj9a3wslqd7zd
        address_n=parse_path("m/86h/1h/1h/0/0"),
        amount=4_450,
        prev_hash=TXHASH_901593,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    inp4 = messages.TxInputType(
        # msUqRgCWS7ryuFcF34EaKTrsTe3xHra128
        address_n=parse_path("m/44h/1h/1h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_3ac32e,
        prev_index=2,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q6xnnna3g7lk22h5tn8nlx2ezmndlvuk556w4w3",
        amount=25_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )
    out2 = messages.TxOutputType(
        address="mfnMbVFC1rH4p9GNbjkMfrAjyKRLycFAzA",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=7_000,
    )
    out3 = messages.TxOutputType(
        address="2MvAG8m2xSf83FgeR4ZpUtaubpLNjAMMoka",
        amount=6_900,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
    )
    out4 = messages.TxOutputType(
        op_return_data=b"test of op_return data",
        amount=0,
        script_type=messages.OutputScriptType.PAYTOOPRETURN,
    )
    out5 = messages.TxOutputType(
        address="tb1ptgp9w0mm89ms43flw0gkrhyx75gyc6qjhtpf0jmt5sv0dufpnsrsyv9nsz",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
    )

    with client:
        client.set_expected_responses(
            [
                # process inputs
                request_input(0),
                request_input(1),
                request_input(2),
                request_input(3),
                # approve outputs
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(2),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(3),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(4),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                (is_core(client), messages.ButtonRequest(code=B.SignTx)),
                messages.ButtonRequest(code=B.SignTx),
                # verify inputs
                request_input(0),
                request_meta(TXHASH_8c3ea7),
                request_input(0, TXHASH_8c3ea7),
                request_output(0, TXHASH_8c3ea7),
                request_output(1, TXHASH_8c3ea7),
                request_input(1),
                request_meta(TXHASH_7956f1),
                request_input(0, TXHASH_7956f1),
                request_input(1, TXHASH_7956f1),
                request_output(0, TXHASH_7956f1),
                request_output(1, TXHASH_7956f1),
                request_input(2),
                request_meta(TXHASH_901593),
                request_input(0, TXHASH_901593),
                request_output(0, TXHASH_901593),
                request_input(3),
                request_meta(TXHASH_3ac32e),
                request_input(0, TXHASH_3ac32e),
                request_output(0, TXHASH_3ac32e),
                request_output(1, TXHASH_3ac32e),
                request_output(2, TXHASH_3ac32e),
                # serialize (segwit) inputs
                request_input(0),
                request_input(1),
                request_input(2),
                # serialize and sign legacy input
                request_input(0),
                request_input(1),
                request_input(2),
                request_input(3),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                # serialize outputs
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                # sign segwit inputs
                request_input(0),
                request_input(1),
                request_input(2),
                (client.model is models.T1B1, request_input(3)),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2, inp3, inp4],
            [out1, out2, out3, out4, out5],
            prev_txes=TX_API,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001045d77b6e482d770031ad3ce3423727cc1707bc2c82e729b1189d2b60aa1a73e8c0000000017160014a33c6e24c99e108b97bc411e7e9ef31e9d5d6164ffffffff7b350e3faca092f39883d7086cdd502c82b6f0314ab61541b062733edef156790000000000ffffffff852e125137abca2dd7a42837dccfc34edc358c72eefd62978d6747d3be9315900000000000ffffffff9b117a776a9aaf70d4c3ffe89f009dcd23210a03d649ee5e38791d83902ec33a020000006b483045022100f6bd64136839b49822cf7e2050bc5c91346fc18b5cf97a945d4fd6c502f712d002207d1859e66d218f705b704f3cfca0c75410349bb1f50623f4fc2d09d5d8df0a3f012103bae960983f83e28fcb8f0e5f3dc1f1297b9f9636612fd0835b768e1b7275fb9dffffffff05a861000000000000160014d1a739f628f7eca55e8b99e7f32b22dcdbf672d4581b0000000000001976a91402e9b094fd98e2a26e805894eb78f7ff3fef199b88acf41a00000000000017a9141ff816cbeb74817050de585ceb2c772ebf71147a870000000000000000186a1674657374206f66206f705f72657475726e206461746110270000000000002251205a02573f7b39770ac53f73d161dc86f5104c6812bac297cb6ba418f6f1219c070247304402205fae7fa2b5141548593d5623ce5bd82ee18dfc751c243526039c91848efd603702200febfbe3467a68c599245ff89055514f26e146c79b58d932ced2325e6dad1b1a0121021630971f20fa349ba940a6ba3706884c41579cd760c89901374358db5dd545b90247304402201b21212100c84207697cebb852374669c382ed97cbd08afbbdfe1b302802161602206b32b2140d094cf5b7e758135961c95478c8e82fea0df30f56ccee284b79eaea012103f6b2377d52960a6094ec158cf19dcf9e33b3da4798c2302aa5806483ed4187ae0140470aaf1a975c27a541de1efbdb5f930ddcc6f3f1765dbd6547a24bba3dc34b682ca5f03e1426b75bee3e9009c92534865362000705f3415ab60d9e7a3e6cfce00000000000"
    )


def test_attack_script_type(client: Client):
    # Scenario: The attacker falsely claims that the transaction is Taproot-only to
    # avoid prev tx streaming and gives a lower amount for one of the inputs. The
    # correct input types and amounts are revelaled only in step6_sign_segwit_inputs()
    # to get a valid signature. This results in a transaction which pays a fee much
    # larger than what the user confirmed.

    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=7_289_000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/1h/0/0"),
        amount=12_300_000,
        prev_hash=TXHASH_091446,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    out1 = messages.TxOutputType(
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=7_289_000 + 10_000 - 1_000,
    )

    attack_count = 5

    def attack_processor(msg):
        nonlocal attack_count

        if attack_count > 0 and msg.tx.inputs:
            attack_count -= 1
            if msg.tx.inputs[0] == inp2:
                msg.tx.inputs[0].amount = 10000
            msg.tx.inputs[0].address_n[0] = H_(86)
            msg.tx.inputs[0].script_type = messages.InputScriptType.SPENDTAPROOT

        return msg

    with client:
        client.set_filter(messages.TxAck, attack_processor)
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                (is_core(client), messages.ButtonRequest(code=B.SignTx)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(TrezorFailure) as exc:
            btc.sign_tx(client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_API)
        assert exc.value.code == messages.FailureType.ProcessError
        assert exc.value.message.endswith("Transaction has changed during signing")


@pytest.mark.parametrize(
    "address",
    (
        # SegWit v1 pubkey not on the curve.
        "tb1pam775nxmvam4pfpqlm5q06k0y84e3x9w0xuhdpmxuna2qj3dfg6qy2pq29",
        # SegWit v1 invalid address length.
        "tb1plycg5qvjtrp3qjf5f7zl382j9x6nrjz9n0dh50",
        # Unrecognized SegWit version.
        "tb1zlycg5qvjtrp3qjf5f7zl382j9x6nrjz9sdhenvyxq8c3808qxmusxanpxu",
        # SegWit v1 pubkey x-coordinate exceeds the field size.
        "tb1pllllllllllllllllllllllllllllllllllllllllllllallllscqgl4zhn",
    ),
)
def test_send_invalid_address(client: Client, address: str):
    inp1 = messages.TxInputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("m/86h/1h/0h/1/0"),
        amount=4_600,
        prev_hash=TXHASH_7956f1,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        address=address,
        amount=4_450,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client, pytest.raises(TrezorFailure):
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.Failure,
            ]
        )
        btc.sign_tx(client, "Testnet", [inp1], [out1], prev_txes=TX_API)


@pytest.mark.multisig
def test_send_multisig_1(client: Client):
    # input tx: e56e8bdb23625856c54f5f52e3edc10ebabd72c839eed41a49f8ec2ea3691363

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/86h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1ph9e923j4w40nhr4v9fqz4pdn09tphdagrcx997qhe2fezgs2dqlqv9r8hl
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[0, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/1h/0/0"),
        prev_hash=TXHASH_e56e8b,
        prev_index=2,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        multisig=multisig,
        amount=4900,
    )

    out1 = messages.TxOutputType(
        address="tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy",
        amount=4900 - 2000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_output(0),
        request_input(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        signatures, _ = btc.sign_tx(client, "Testnet", [inp1], [out1])

    # store signature
    inp1.multisig.signatures[0] = signatures[0]
    # sign with third key
    inp1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(client, "Testnet", [inp1], [out1])

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/29e67f2b9239a2bea3840a664077bca7df751fcfdd9d962e337e3f6ade15c0a5",
        tx_hex="01000000000101631369a32eecf8491ad4ee39c872bdba0ec1ede3525f4fc556586223db8b6ee50200000000ffffffff01540b000000000000220020c5f4a0a4ea7c0392efe0a9670a73264cffa90b19107cd8a8e9750ff93c77fdfb05407947a9308e19a0ec87e89211a5f4a108e69f6ebb2347eb289bfdf531464e97489736730f76131a5b3a9836d3716005ca49fcb4764be54956fab6ce05aad76a69004023c0143ff50681e0d94efcf46aec6cf5a899cf64dea629c5d9239f1061ba0eff6b52f0862e05ec7a313b08e09db3b9651d5345c58711b924fa3f9e51864e2621682061465959e55a05157db83f9785fc1f080495303f501c1ae262d8548beef6f46cac20e468fb01bde3718a826107ad3dff1dfb766f6a37ae880b779c2305601da2dd8aba2022988c4042826838fcb3e95ab0211b207034b1d3abefc0efe49a493dcb975aaaba529c21c14a30b2e461b280c0b13a03799096ab1256589153fc4b9c8cead16dc0b642069700000000",
    )


@pytest.mark.multisig
def test_send_multisig_2(client: Client):
    # input tx: b84fd297347318ff6693513637b11005600f93f4af60a44ffebaea1b5637d06c

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/86h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1p8wk2er5shm22z5mqy3qn2al7gz62csw75uh4ag8wluzptgr387tqeynquu
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[0, 1],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/2h/0/1"),
        prev_hash=TXHASH_b84fd2,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        multisig=multisig,
        amount=10_551,
    )

    out1 = messages.TxOutputType(
        address="tb1qr6xa5v60zyt3ry9nmfew2fk5g9y3gerkjeu6xxdz7qga5kknz2ssld9z2z",
        amount=10_551 - 5_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_output(0),
        request_input(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        signatures, _ = btc.sign_tx(client, "Testnet", [inp1], [out1])

    # store signature
    inp1.multisig.signatures[1] = signatures[0]
    # sign with first key
    inp1.address_n[2] = H_(1)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(client, "Testnet", [inp1], [out1])

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/18c12c869657f28901df61b2a72499cdbb52a1249552a12041d14fb2ff3b1e64",
        tx_hex="010000000001016cd037561beabafe4fa460aff4930f600510b13736519366ff18733497d24fb80000000000ffffffff01af150000000000002200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a105004018ef361f578ee11b438c5b95673d38a550f324be69a2a3b133c79926b9a1a48c31d20672c6145ed0579f0478b7997a56be57f2982e6ccabef0a962c54c432e4e4000d5a6434e4a446d75f0e6d185a910998d7bb9511a85f6da46824fe5d197aaf40ca8776a59576fc0ced6044d14ef2e4fc33d85cd067a29335aaf09cc05609cd86820d7a2c22a7e60ea8084288b7c8f400ebb6d815ec09d1cba8aca060ec11506ce8dac20eabf4a439218264d990911f8c74579e8db3a72835c5f4093638badfb8a4bf766ba20a58003e084b3998fbeec35d4f6785873aab37b413e66c45f87943ada3183e645ba529c21c0a6d4674217688a33aaf77d815c52cb6739f8bc7abfb25567759515ab7cd6fc3700000000",
    )


@pytest.mark.multisig
def test_send_multisig_3_change(client: Client):
    # input tx: bedf7b99c7e8e92f64d233c3789ba265671b89b1ab048296243a27da872f6494

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/86h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1pnk26euz34ftr0pmu4ygptk4829rua5s20fvm2ykrn5sfvdkgtwpss4uqax
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )
    multisig2 = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[1, 1],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/1h/1/0"),
        prev_hash=TXHASH_bedf7b,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        multisig=multisig,
        amount=28_705,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/86h/1h/1h/1/1"),
        amount=28_705 - 10_000,
        multisig=multisig2,
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
    )

    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_output(0),
        request_input(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        signatures, _ = btc.sign_tx(client, "Testnet", [inp1], [out1])

    # store signature
    inp1.multisig.signatures[0] = signatures[0]
    # sign with third key
    inp1.address_n[2] = H_(3)
    out1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        _, serialized_tx = btc.sign_tx(client, "Testnet", [inp1], [out1])

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/4670d37ad9d8cd92f7712e9ff90503c96d20201ab7c19b9621d3d9c00450c3ac",
        tx_hex="0100000000010194642f87da273a24968204abb1891b6765a29b78c333d2642fe9e8c7997bdfbe0000000000ffffffff01114900000000000022512011901dcb350069ceb9d16c30805197f147f4dbad6c59e7c875eb3ddda47182b60540a40d516fe8f52e99d4a25d34b466e31d09fd8a7785a1441d1148d4eb0e767c96f4c78135ddd2cbe412789944631312f7f3ffcb40612d76062bf5cba8f6e676c3004075b5624ccca6ee82fda05f1cd9b72fe181db1b28ec48c2d416d0bb84ef17b8b06d6f7e2167588b1acb9984fbf60b938960f2c5ae2b3d7d1c93aa2c93091761856820852e4ec4dfd12b7414503d2746abc58ffcb626d401e17fe4b8b75e3a2ece8147ac20984a838226f2a655812683b00a26a3d413538daec64e4e135e5e8b0f6c0438d2ba20cd53e7d320770e1edc1619efaeda211d068ad77f00fe8376bb6c5aa6494dd406ba529c21c1a24cedfcfebb0c81e572c3b6a4135c906f47f9a00d162cc26ffd8897e6772c4500000000",
    )


@pytest.mark.multisig
def test_send_multisig_4_change(client: Client):
    # input tx: d20c2e9f00220048a20e9a7240a9f41d57ca29541009d3477316233416946145

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/86h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1pzxgpmje4qp5uaww3dscgq5vh79rlfkadd3v70jr4av7amfr3s2mqw93kgy
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[1, 1],
        signatures=[b"", b"", b""],
        m=2,
    )
    multisig2 = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[1, 2],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/1h/1/1"),
        prev_hash=TXHASH_d20c2e,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        multisig=multisig,
        amount=4_900,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/86h/1h/1h/1/2"),
        amount=4_900 - 2_000,
        multisig=multisig2,
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
    )

    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_output(0),
        request_input(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        signatures, _ = btc.sign_tx(client, "Testnet", [inp1], [out1])

    # store signature
    inp1.multisig.signatures[0] = signatures[0]
    # sign with third key
    inp1.address_n[2] = H_(3)
    out1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        _, serialized_tx = btc.sign_tx(client, "Testnet", [inp1], [out1])

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/a23d30e520c9d0c4bccd04052ce18c90144e40dd4c0ac93f245830c5b6a4904b",
        tx_hex="01000000000101456194163423167347d309105429ca571df4a940729a0ea2480022009f2e0cd20000000000ffffffff01540b0000000000002251204c9005ce3af7e9e0431f495bff1cf76de4cf26b8fb120ad0e520e5afe184a36c0540f9a77d5b4426e545bf1f34a26ff2407e87a8d5440ab67104eaa2063bb0cf46094e9351a7fa0eefe74b3dc5082855b2586b9cc9c6fe5cd1d3a8ff78687f5be08d00403cf6027e390f6381764c1918498d3f9a18746649e1d9a4661a5ec8ef64c2c41520da013cc1b88f68b7fccbce62714ec8022f09363e749b4e9e77fa2541ea732968208ed908dd8424b93b4b713d1d889e8d3d7c8ac58ddaf5bb47d2172fca760a223bac20575123f284fc0749e9ec186dc5318ea1126431d42cb88b5ea0f3d6dd31ccbe26ba209dc1f7e86ecf62eb89d00a2a16aa37744cbfd52e210779fbe0892246d1b7059eba529c21c14190a45076828ce7bfe18486671eef3f143fb41dd13e0fa0ba24813e33f9a8cf00000000",
    )
