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
from trezorlib.tools import H_, parse_path

from ...bip32 import deserialize
from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
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
TXHASH_ec16dc = bytes.fromhex(
    "ec16dc5a539c5d60001a7471c37dbb0b5294c289c77df8bd07870b30d73e2231"
)
TXHASH_b36780 = bytes.fromhex(
    "b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e"
)
TXHASH_fcb3f5 = bytes.fromhex(
    "fcb3f5436224900afdba50e9e763d98b920dfed056e552040d99ea9bc03a9d83"
)
TXHASH_d159fd = bytes.fromhex(
    "d159fd2fcb5854a7c8b275d598765a446f1e2ff510bf077545a404a0c9db65f7"
)
TXHASH_65047a = bytes.fromhex(
    "65047a2b107d6301d72d4a1e49e7aea9cf06903fdc4ae74a4a9bba9bc1a414d2"
)
TXHASH_b9abfa = bytes.fromhex(
    "b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6"
)
TXHASH_1c022d = bytes.fromhex(
    "1c022d9da3aa8bc8cf2a617c42c8f2c343e810af76b3ab9770c5ab6ca54ddab5"
)


def test_send_p2sh(client: Client):
    # input tx: 20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=123_456_789 - 11_000 - 12_300_000,
    )
    with client:
        is_core = client.features.model in ("T", "Safe 3")
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
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a",
        tx_hex="0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100bd3d8b8ad35c094e01f6282277300e575f1021678fc63ec3f9945d6e35670da3022052e26ef0dd5f3741c9d5939d1dec5464c15ab5f2c85245e70a622df250d4eb7c012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000",
    )


def test_send_p2sh_change(client: Client):
    # input tx: 20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/49h/1h/0h/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123_456_789 - 11_000 - 12_300_000,
    )
    with client:
        is_core = client.features.model in ("T", "Safe 3")
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
        == "0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100bd3d8b8ad35c094e01f6282277300e575f1021678fc63ec3f9945d6e35670da3022052e26ef0dd5f3741c9d5939d1dec5464c15ab5f2c85245e70a622df250d4eb7c012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000"
    )


def test_send_native(client: Client):
    # input tx: b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e

    inp1 = messages.TxInputType(
        # tb1qajr3a3y5uz27lkxrmn7ck8lp22dgytvagr5nqy
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_b36780,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=40_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="tb1qe48wz5ysk9mlzhkswcxct9tdjw6ejr2l9e6j8q",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=100_000 - 40_000 - 10_000,
    )
    with client:
        is_core = client.features.model in ("T", "Safe 3")
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
                request_meta(TXHASH_b36780),
                request_input(0, TXHASH_b36780),
                request_output(0, TXHASH_b36780),
                request_output(1, TXHASH_b36780),
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

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/65047a2b107d6301d72d4a1e49e7aea9cf06903fdc4ae74a4a9bba9bc1a414d2",
        tx_hex="010000000001019e2123e595e20d6aa2c8d227b2b98c781b8b41fda635756eca0768b8ce8067b30000000000ffffffff02409c00000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c98750c3000000000000160014cd4ee15090b177f15ed0760d85956d93b5990d5f0247304402200c734ed16a9226162a29133c14fad3565332c60346050ceb9246e73a2fc8485002203463d40cf78eb5cc9718d6617d9f251b987e96cb58525795a507acb9b91696c7012103f60fc56bf7b5326537c7e86e0a63b6cd008eeb87d39af324cee5bcc3424bf4d000000000",
    )


def test_send_to_taproot(client: Client):
    # input tx: ec16dc5a539c5d60001a7471c37dbb0b5294c289c77df8bd07870b30d73e2231

    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_ec16dc,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1pdvdljpj774356dpk32c2ks0yqv7q7c4f98px2d9e76s73vpudpxs7tl6vp",
        amount=7_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="tb1qcc4ext5rsa8pzqa2m030jk670wmn5f649pu7sr",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=10_000 - 7_000 - 200,
    )
    with client:
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/4f7ad10322f7d1be86ac03997cb6bcad852b8937e504de5779dfcf313edf300e",
        tx_hex="0100000000010131223ed7300b8707bdf87dc789c294520bbb7dc371741a00605d9c535adc16ec0000000000ffffffff02581b0000000000002251206b1bf9065ef5634d34368ab0ab41e4033c0f62a929c26534b9f6a1e8b03c684df00a000000000000160014c62b932e83874e1103aadbe2f95b5e7bb73a275502473044022008ce0e893e91935ada9a31fe6b2f6228070dd2a5bdebc413429e658be761901502207086e0d3aa6abbad29c966444d3b791e43c174f88154381d07c92a84fec7c527012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000",
    )


def test_send_native_change(client: Client):
    # input tx: fcb3f5436224900afdba50e9e763d98b920dfed056e552040d99ea9bc03a9d83

    inp1 = messages.TxInputType(
        # tb1qajr3a3y5uz27lkxrmn7ck8lp22dgytvagr5nqy
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_fcb3f5,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",  # m/49h/1h/0h/0/0
        amount=40_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/0h/1/87"),
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        amount=100_000 - 40_000 - 10_000,
    )
    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_fcb3f5),
                request_input(0, TXHASH_fcb3f5),
                request_input(1, TXHASH_fcb3f5),
                request_output(0, TXHASH_fcb3f5),
                request_output(1, TXHASH_fcb3f5),
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

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/2161a89815814c3866f5953c1e59a977f7cd5432c731cd5633378cfc3fb87fdd",
        tx_hex="01000000000101839d3ac09bea990d0452e556d0fe0d928bd963e7e950bafd0a90246243f5b3fc0000000000ffffffff02409c00000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c98750c3000000000000160014cc3e33b1eb529cea8b34af5d2c5d6e6e332de9040247304402207413e26bf9eff16513f5ed1db710aa6f766b51f6c6f23ad5e9e8ddf5c67e8aba02204e09b0755ec173f6beeb8ddfa515d36afb25f046d0c851d48fdbc2e0ad3b9f13012103f60fc56bf7b5326537c7e86e0a63b6cd008eeb87d39af324cee5bcc3424bf4d000000000",
    )


def test_send_both(client: Client):
    # input 1 tx: 65047a2b107d6301d72d4a1e49e7aea9cf06903fdc4ae74a4a9bba9bc1a414d2
    # input 2 tx: d159fd2fcb5854a7c8b275d598765a446f1e2ff510bf077545a404a0c9db65f7

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/0/0"),  # 2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp
        amount=40_000,
        prev_hash=TXHASH_65047a,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=25_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=35_000,
    )
    out3 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=100_000 + 40_000 - 25_000 - 35_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(2),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                (is_core, messages.ButtonRequest(code=B.SignTx)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_65047a),
                request_input(0, TXHASH_65047a),
                request_output(0, TXHASH_65047a),
                request_output(1, TXHASH_65047a),
                request_input(1),
                request_meta(TXHASH_d159fd),
                request_input(0, TXHASH_d159fd),
                request_output(0, TXHASH_d159fd),
                request_output(1, TXHASH_d159fd),
                request_output(2, TXHASH_d159fd),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(2),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2, out3],
            prev_txes=TX_API_TESTNET,
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/9012ec5daf9f09d79ab7ed63d1881f1e114a4ecc3754208d9254300bbdd8812e",
        tx_hex="01000000000102d214a4c19bba9b4a4ae74adc3f9006cfa9aee7491e4a2dd701637d102b7a046500000000171600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5cfffffffff765dbc9a004a4457507bf10f52f1e6f445a7698d575b2c8a75458cb2ffd59d10000000000ffffffff03a861000000000000160014a579388225827d9f2fe9014add644487808c695db88800000000000017a91491233e24a9bf8dbb19c1187ad876a9380c12e7878770110100000000001976a914a579388225827d9f2fe9014add644487808c695d88ac024730440220109f615c54b409fde8292ff27529dea51497ac6c72d83e555146cfb817e64cda02203b06c0d5ca3529ab56e0ad5fae44184f56afe1fec187ba00e2cb0da387ea7f7e0121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf0248304502210097f6be59665df66777e9804c92ac7c770089f532ce3668be9abc687f6a6f60290220634433824ad8dca5f20a3907d6e370312fdcb652434f6398f1bebe61858cf1cb012103f60fc56bf7b5326537c7e86e0a63b6cd008eeb87d39af324cee5bcc3424bf4d000000000",
    )


@pytest.mark.multisig
def test_send_multisig_1(client: Client):
    # input tx: b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/49h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # 2NFe7UAaccZxavBstpqDPkDasTGR154uvzT
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[0, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/1h/0/0"),
        prev_hash=TXHASH_b9abfa,
        prev_index=4,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address="tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy",
        amount=100_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_b9abfa),
        request_input(0, TXHASH_b9abfa),
        request_output(0, TXHASH_b9abfa),
        request_output(1, TXHASH_b9abfa),
        request_output(2, TXHASH_b9abfa),
        request_output(3, TXHASH_b9abfa),
        request_output(4, TXHASH_b9abfa),
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
        hash_link="https://tbtc1.trezor.io/api/tx/3ec03ab3487655f88e13063b71882af5f52d1db6f622b50190035d7260517d50",
        tx_hex="01000000000101a660b551efbe3f6e79b181d3c4445a7c3ffc4b970f6c1f5ef2f6284a0dfaabb904000000232200208d398cfb58a1d9cdb59ccbce81559c095e8c6f4a3e64966ca385078d9879f95effffffff01905f010000000000220020c5f4a0a4ea7c0392efe0a9670a73264cffa90b19107cd8a8e9750ff93c77fdfb040047304402203f3309fce4beab5131917615996ae79308a36043d46a52865f39d22e2f2b7abd02207d7f2e1cf1e0029192c33a5466e7717f906b8bfd512ba8c1264490691dc0d94601483045022100a154ab8162ef7328d82fc70b288ce422752bf4635626d30b467eb08985025441022065636e0537e10493dd82c0385252bde81d161236b092fcae8de359b253da41fd01695221021630971f20fa349ba940a6ba3706884c41579cd760c89901374358db5dd545b92102f2ff4b353702d2bb03d4c494be19d77d0ab53d16161b53fbcaf1afeef4ad0cb52103e9b6b1c691a12ce448f1aedbbd588e064869c79fbd760eae3b8cd8a5f1a224db53ae00000000",
    )


@pytest.mark.multisig
def test_send_multisig_2(client: Client):
    # input tx: b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/84h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1qauuv4e2pwjkr4ws5f8p20hu562jlqpe5h74whxqrwf7pufsgzcms9y8set
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[0, 1],
        signatures=[b"", b"", b""],
        m=2,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/2h/0/1"),
        prev_hash=TXHASH_b9abfa,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
        multisig=multisig,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address="tb1qr6xa5v60zyt3ry9nmfew2fk5g9y3gerkjeu6xxdz7qga5kknz2ssld9z2z",
        amount=100_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_b9abfa),
        request_input(0, TXHASH_b9abfa),
        request_output(0, TXHASH_b9abfa),
        request_output(1, TXHASH_b9abfa),
        request_output(2, TXHASH_b9abfa),
        request_output(3, TXHASH_b9abfa),
        request_output(4, TXHASH_b9abfa),
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
    inp1.multisig.signatures[1] = signatures[0]
    # sign with first key
    inp1.address_n[2] = H_(1)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/2aad59bad0dd1ad3e9b2a4019bbb47c16111d5a2eddde50997e4199c26ee5882",
        tx_hex="01000000000101a660b551efbe3f6e79b181d3c4445a7c3ffc4b970f6c1f5ef2f6284a0dfaabb90100000000ffffffff01905f0100000000002200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a10400483045022100ab35a9f9f915ed4d2017237c12d4676545bdf124c5b1c552e9e23777e601372b02202aee125c86a4255102ccba2ea0c5e7d42bb16f4b183a4cde3e707379574d61500147304402204ab0b571d1f4a37cf94cb3644f261483bcfa387d6a9f3631720d0966bf9248cf0220650b1f928343600b7eedc929902c9b16bf0f00431643b05642fdcf1ae1fd72af0169522103bab8ecdd9ae2c51a0dc858f4c751b27533143bf6013ba1725ba8a4ecebe7de8c21027d5e55696c875308b03f2ca3d8637f51d3e35da9456a5187aa14b3de8a89534f2103b78eabaea8b3a4868be4f4bb96d6f66973f7081faa7f1cafba321444611c241e53ae00000000",
    )


@pytest.mark.multisig
def test_send_multisig_3_change(client: Client):
    # input tx: b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/84h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # tb1ql8zsl5jvpvue4xuf2dqc2w73ejcthuyrjxasuwm9z58fsxwkut9sw3trx9
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
        address_n=parse_path("m/84h/1h/1h/1/0"),
        prev_hash=TXHASH_b9abfa,
        prev_index=2,
        script_type=messages.InputScriptType.SPENDWITNESS,
        multisig=multisig,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/1h/1/1"),
        amount=100_000 - 10_000,
        multisig=multisig2,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
    )

    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.UnknownDerivationPath),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_b9abfa),
        request_input(0, TXHASH_b9abfa),
        request_output(0, TXHASH_b9abfa),
        request_output(1, TXHASH_b9abfa),
        request_output(2, TXHASH_b9abfa),
        request_output(3, TXHASH_b9abfa),
        request_output(4, TXHASH_b9abfa),
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
    out1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/16bfb04cd202a9aab41dcc3c73504f5a342345b1e1420d934a91b49c2447029d",
        tx_hex="01000000000101a660b551efbe3f6e79b181d3c4445a7c3ffc4b970f6c1f5ef2f6284a0dfaabb90200000000ffffffff01905f01000000000017a914536250d41937e5b641082447580ff6a8e46c122a8704004730440220020e4bd3e7173769e82ddb10c101f612d5ef91197983015de9d20f556992bdb4022019f6e3774d1b96d6e82605f3919e5b306035c58c8f3023d12dfdfc9ececebdbe01483045022100e9175e1032d03761740f36c336f38b0b586659d74d57f89a301df551f934f29c02207a52b5a24a85a6344f4fd0b1d51f37a61408b75f3f21a7df5727196cbd2513d701695221039dba3a72f5dc3cad17aa924b5a03c34561465f997d0cb15993f2ca2c0be771c42103cd39f3f08bbd508dce4d307d57d0c70c258c285878bfda579fa260acc738c25d2102cd631ba95beca1d64766f5540885092d0bb384a3c13b6c3a5334d0ebacf51b9553ae00000000",
    )


@pytest.mark.multisig
def test_send_multisig_4_change(client: Client):
    # input tx: b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/49h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    # 2MxuPZQqtLTPJQWcLL9oLVZAKRAGy6mq4Po
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
        address_n=parse_path("m/49h/1h/1h/1/1"),
        prev_hash=TXHASH_b9abfa,
        prev_index=3,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/49h/1h/1h/1/2"),
        amount=100_000 - 10_000,
        multisig=multisig2,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.UnknownDerivationPath),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_b9abfa),
        request_input(0, TXHASH_b9abfa),
        request_output(0, TXHASH_b9abfa),
        request_output(1, TXHASH_b9abfa),
        request_output(2, TXHASH_b9abfa),
        request_output(3, TXHASH_b9abfa),
        request_output(4, TXHASH_b9abfa),
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
    out1.address_n[2] = H_(3)

    with client:
        client.set_expected_responses(expected_responses)
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/b006619cf84ff4f36cfbd9a4f77a77678cc1b040d81b118c745dce5bbfe255d5",
        tx_hex="01000000000101a660b551efbe3f6e79b181d3c4445a7c3ffc4b970f6c1f5ef2f6284a0dfaabb90300000023220020fa6c73de618ec134eeec0c16f6dd04d46d4347e9a4fd0a95fd7938403a4949f9ffffffff01905f010000000000220020bcea2324dacbcde5a9db90cc26b8df9cbc72010e05cb68cf034df6f0e05239a20400473044022046de6458d0e1d7fcc1945d6ee027d5900c7ba18183416813a9b841c5b57b7417022011cfaa89ce7f60c876d569f51080e0f9e07c09ec34fbdbc3b0e26f1028e23e2501473044022027909365f0c3d2743ba2970e74ef2c375d0ae00243e2d75d206c075d6a0f219202206a429e7e6355f8a6e957d539add1d6a24533a20f5023d19e7c2aaf25221024c501695221036a5ec3abd10501409092246fe59c6d7a15fff1a933479483c3ba98b866c5b9742103559be875179d44e438db2c74de26e0bc9842cbdefd16018eae8a2ed989e474722103067b56aad037cd8b5f569b21f9025b76470a72dc69457813d2b76e98dc0cd01a53ae00000000",
    )


def test_multisig_mismatch_inputs_single(client: Client):
    # Ensure that if there is a non-multisig input, then a multisig output
    # will not be identified as a change output.

    # m/84'/1'/0' for "alcohol woman abuse ..." seed.
    node_int = deserialize(
        "Vpub5kFDCYhiYuAzjk7TBQPNFffbexHF7iAd8AVVgHQKUany7e6NQvthgk86d7DfH57DY2dwBK4PyVTDDaS1r2gjkdyJyUYGoV9qNujGSrW9Dpe"
    )

    # m/84'/1'/0' for "all all ... all" seed.
    node_ext = deserialize(
        "Vpub5jR76XyyhBaQXPSRf3PBeY3gF914d9sf7DWFVhMESEQMCdNv35XiVvp8gZsFXAv222VPHLNnAEXxMPG8DPiSuhAXfEydBf55LTLBGHCDzH2"
    )

    # tb1qpzmgzpcumztvmpu3q27wwdggqav26j9dgks92pvnne2lz9ferxgssmhzlq
    multisig_in = messages.MultisigRedeemScriptType(
        nodes=[node_int, node_ext], address_n=[0, 0], signatures=[b"", b""], m=1
    )

    multisig_out = messages.MultisigRedeemScriptType(
        nodes=[node_int, node_ext], address_n=[1, 0], signatures=[b"", b""], m=1
    )

    inp1 = messages.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=100_000,
        prev_hash=TXHASH_1c022d,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_1c022d,
        prev_index=2,
        script_type=messages.InputScriptType.SPENDWITNESS,
        multisig=multisig_in,
        amount=100_000,
    )

    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/0h/1/0"),
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        multisig=multisig_out,
        amount=100_000 + 100_000 - 50_000 - 10_000,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                # Ensure that the multisig output is not identified as a change output.
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_1c022d),
                request_input(0, TXHASH_1c022d),
                request_output(0, TXHASH_1c022d),
                request_output(1, TXHASH_1c022d),
                request_output(2, TXHASH_1c022d),
                request_input(1),
                request_meta(TXHASH_1c022d),
                request_input(0, TXHASH_1c022d),
                request_output(0, TXHASH_1c022d),
                request_output(1, TXHASH_1c022d),
                request_output(2, TXHASH_1c022d),
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
            client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/d3b2ec2a540363ffbb231c6cf0a311ec84c8404c7ec2819c146dfb90a69c593a",
        tx_hex="01000000000102b5da4da56cabc57097abb376af10e843c3f2c8427c612acfc88baaa39d2d021c0100000000ffffffffb5da4da56cabc57097abb376af10e843c3f2c8427c612acfc88baaa39d2d021c0200000000ffffffff0250c300000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987e022020000000000220020733ecfbbe7e47a74dde6c7645b60cdf627e90a585cde7733bc7fdaf9fe30b3740247304402207076385a688713bd380d7e01858254161c11981a0f549098c77ab8afbaec38b40220713854182527e3f32e6910b7a4c5154969039e665bdec0ab4e12e2d3a9543e65012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86203004730440220096cf4bff1590e005ff86cf10462b320b9b0eccfc45b8ea4badd276ad9cc536702207502c0dc037f64c58fde74925b4593dcd842d76085538083b6450bf9e73384420147512103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d2103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86252ae00000000",
    )
