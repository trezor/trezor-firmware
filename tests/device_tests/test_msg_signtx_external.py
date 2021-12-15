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

from trezorlib import btc, messages as proto
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = proto.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)
TXHASH_d830b8 = bytes.fromhex(
    "d830b877c3d9237a0a68be88825a296da01ac282a2efd2f671d8f17f15117b74"
)
TXHASH_091446 = bytes.fromhex(
    "09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a"
)
TXHASH_65b811 = bytes.fromhex(
    "65b811d3eca0fe6915d9f2d77c86c5a7f19bf66b1b1253c2c51cb4ae5f0c017b"
)
TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
TXHASH_70f987 = bytes.fromhex(
    "70f9871eb03a38405cfd7a01e0e1448678132d815e2c9f552ad83ae23969509e"
)
TXHASH_65b768 = bytes.fromhex(
    "65b768dacccfb209eebd95a1fb80a04f1dd6a3abc6d7b41d5e9d9f91605b37d9"
)
TXHASH_a345b8 = bytes.fromhex(
    "a345b85759b385c6446055e4c3baa77e8161a65009dc009489b48aa6587ce348"
)
TXHASH_3ac32e = bytes.fromhex(
    "3ac32e90831d79385eee49d6030a2123cd9d009fe8ffc3d470af9a6a777a119b"
)
TXHASH_df862e = bytes.fromhex(
    "df862e31da31ff84addd392f6aa89af18978a398ea258e4901ae72894b66679f"
)


@pytest.mark.skip_t1
def test_p2pkh_presigned(client):
    inp1 = proto.TxInputType(
        # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        amount=31000000,
    )

    inp1ext = proto.TxInputType(
        # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        # address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        amount=31000000,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914a579388225827d9f2fe9014add644487808c695d88ac"
        ),
        script_sig=bytes.fromhex(
            "473044022054fa66bfe1de1c850d59840f165143a66075bae78be3a6bc2809d1ac09431d380220019ecb086e16384f18cbae09b02bd2dce18763cd06454d33d93630561250965e0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        ),
    )

    inp2 = proto.TxInputType(
        # mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b
        address_n=parse_path("m/44h/1h/0h/0/1"),
        prev_hash=TXHASH_d830b8,
        prev_index=1,
        amount=600000000,
    )

    inp2ext = proto.TxInputType(
        # mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b
        # address_n=parse_path("m/44h/1h/0h/0/1"),
        prev_hash=TXHASH_d830b8,
        prev_index=1,
        amount=600000000,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a9145b157a678a10021243307e4bb58f36375aa80e1088ac"
        ),
        script_sig=bytearray.fromhex(
            "463043021f3a0a7fdf27b340358ddf8b4e6e3e6cc0be728d6f1d9d3413ae59741f57599002204809d59a9432a2c7fcb10639c5efa82935d8c3cc21b185ff5e44f0e1a80e635401210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852"
        ),
    )

    out1 = proto.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=620000000,
        script_type=proto.OutputScriptType.PAYTOWITNESS,
    )

    out2 = proto.TxOutputType(
        address_n=parse_path("44h/1h/0h/1/0"),
        amount=31000000 + 600000000 - 620000000 - 10000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )

    # Test with first input as pre-signed external.
    with client:
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1ext, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )

    expected_tx = "0100000002cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006a473044022054fa66bfe1de1c850d59840f165143a66075bae78be3a6bc2809d1ac09431d380220019ecb086e16384f18cbae09b02bd2dce18763cd06454d33d93630561250965e0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff747b11157ff1d871f6d2efa282c21aa06d295a8288be680a7a23d9c377b830d80100000069463043021f3a0a7fdf27b340358ddf8b4e6e3e6cc0be728d6f1d9d3413ae59741f57599002204809d59a9432a2c7fcb10639c5efa82935d8c3cc21b185ff5e44f0e1a80e635401210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852ffffffff020073f424000000001600149c02608d469160a92f40fdf8c6ccced029493088b0b1a700000000001976a9143d3cca567e00a04819742b21a696a67da796498b88ac00000000"
    assert serialized_tx.hex() == expected_tx

    # Test with second input as pre-signed external.
    with client:
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2ext],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert serialized_tx.hex() == expected_tx

    # Test corrupted signature in scriptsig.
    inp2ext.script_sig[10] ^= 1
    with pytest.raises(TrezorFailure, match="Invalid signature"):
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2ext],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )


@pytest.mark.skip_t1
def test_p2wpkh_in_p2sh_presigned(client):
    inp1 = proto.TxInputType(
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=111145789,
        prev_hash=TXHASH_091446,
        prev_index=1,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87"),
        script_sig=bytearray.fromhex("160014d16b8c0680c61fc6ed2e407455715055e41052f5"),
        witness=bytes.fromhex(
            "02483045022100ead79ee134f25bb585b48aee6284a4bb14e07f03cc130253e83450d095515e5202201e161e9402c8b26b666f2b67e5b668a404ef7e57858ae9a6a68c3837e65fdc69012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b79"
        ),
    )
    inp2 = proto.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=proto.InputScriptType.SPENDWITNESS,
    )
    out1 = proto.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=12300000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )
    out2 = proto.TxOutputType(
        # address_n=parse_path("44'/1'/0'/0/0"),
        address="2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc",
        script_type=proto.OutputScriptType.PAYTOADDRESS,
        amount=45600000,
    )
    out3 = proto.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=111145789 + 7289000 - 11000 - 12300000 - 45600000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(2),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_091446),
                request_input(0, TXHASH_091446),
                request_output(0, TXHASH_091446),
                request_output(1, TXHASH_091446),
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
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "010000000001028a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090100000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff03e0aebb0000000000160014a579388225827d9f2fe9014add644487808c695d00cdb7020000000017a91491233e24a9bf8dbb19c1187ad876a9380c12e787870d859b03000000001976a914a579388225827d9f2fe9014add644487808c695d88ac02483045022100ead79ee134f25bb585b48aee6284a4bb14e07f03cc130253e83450d095515e5202201e161e9402c8b26b666f2b67e5b668a404ef7e57858ae9a6a68c3837e65fdc69012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7902463043021f585c54a84dc7326fa60e22729accd41153c7dd4725bd4c8f751aa3a8cd8d6a0220631bfd83fc312cc6d5d129572a25178696d81eaf50c8c3f16c6121be4f4c029d012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
    )

    # Test corrupted script hash in scriptsig.
    inp1.script_sig[10] ^= 1
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(2),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_091446),
                request_input(0, TXHASH_091446),
                request_output(0, TXHASH_091446),
                request_output(1, TXHASH_091446),
                proto.Failure(code=proto.FailureType.DataError),
            ]
        )

        with pytest.raises(TrezorFailure, match="Invalid public key hash"):
            btc.sign_tx(
                client,
                "Testnet",
                [inp1, inp2],
                [out1, out2, out3],
                prev_txes=TX_CACHE_TESTNET,
            )


@pytest.mark.skip_t1
def test_p2wpkh_presigned(client):
    inp1 = proto.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_70f987,
        prev_index=0,
        amount=100000,
        script_type=proto.InputScriptType.SPENDWITNESS,
    )

    inp2 = proto.TxInputType(
        # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
        # address_n=parse_path("m/84h/1h/0h/0/1"),
        prev_hash=TXHASH_65b768,
        prev_index=0,
        amount=10000,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014fb7e49f4017dc951615dea221b66626189aa43b9"),
        script_sig=bytes.fromhex(""),
        witness=bytearray.fromhex(
            "024730440220432ac60461de52713ad543cbb1484f7eca1a72c615d539b3f42f5668da4501d2022063786a6d6940a5c1ed9c2d2fd02cef90b6c01ddd84829c946561e15be6c0aae1012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03"
        ),
    )

    out1 = proto.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=50000,
        script_type=proto.OutputScriptType.PAYTOWITNESS,
    )

    out2 = proto.TxOutputType(
        address_n=parse_path("84h/1h/0h/1/0"),
        amount=100000 + 10000 - 50000 - 1000,
        script_type=proto.OutputScriptType.PAYTOWITNESS,
    )

    # Test with second input as pre-signed external.
    with client:
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "010000000001029e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700000000000ffffffffd9375b60919f9d5e1db4d7c6aba3d61d4fa080fba195bdee09b2cfccda68b7650000000000ffffffff0250c30000000000001600149c02608d469160a92f40fdf8c6ccced02949308878e6000000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b0247304402207be75627767e59046da2699328ca1c27b60cfb34bb257a9d90442e496b5f936202201f43e2b55e1b2acf5677d3e29b9c5a78e2a4ae03a01be5c50a17cf4b88a3b278012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862024730440220432ac60461de52713ad543cbb1484f7eca1a72c615d539b3f42f5668da4501d2022063786a6d6940a5c1ed9c2d2fd02cef90b6c01ddd84829c946561e15be6c0aae1012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d0300000000"
    )

    # Test corrupted signature in witness.
    inp2.witness[10] ^= 1
    with pytest.raises(TrezorFailure, match="Invalid signature"):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )


@pytest.mark.skip_t1
def test_p2wsh_external_presigned(client):
    inp1 = proto.TxInputType(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=12300000,
        prev_hash=TXHASH_091446,
        prev_index=0,
        script_type=proto.InputScriptType.SPENDWITNESS,
    )

    inp2 = proto.TxInputType(
        # 1-of-2 multisig
        # m/84'/1'/0/0/0' for "alcohol woman abuse ..." seed.
        # m/84'/1'/0/0/0' for "all all ... all" seed.
        # tb1qpzmgzpcumztvmpu3q27wwdggqav26j9dgks92pvnne2lz9ferxgssmhzlq
        prev_hash=TXHASH_a345b8,
        prev_index=0,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "002008b681071cd896cd879102bce735080758ad48ad45a05505939e55f115391991"
        ),
        amount=100,
        witness=bytearray.fromhex(
            "030047304402206b570b99c22c841548a35a9b9c673fa3b87a9563ed64ad7d979aa3e01b2e303802201d0bebf58b7243e09798e734fc32892936c4d0c4984bec755dc951ef646e4a9a0147512103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d2103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86252ae"
        ),
    )

    out1 = proto.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=12300000 + 100 - 10000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_091446),
                request_input(0, TXHASH_091446),
                request_output(0, TXHASH_091446),
                request_output(1, TXHASH_091446),
                request_input(1),
                request_meta(TXHASH_a345b8),
                request_input(0, TXHASH_a345b8),
                request_output(0, TXHASH_a345b8),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_TESTNET
        )

    assert (
        serialized_tx.hex()
        == "010000000001028a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff48e37c58a68ab4899400dc0950a661817ea7bac3e4556044c685b35957b845a30000000000ffffffff013488bb000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c9870247304402204270cf602ec151e72b99c5048755379c368c6c7cd722e4234ad4bb7b1b87d09d02207fa59b1c2926ea6b4f0094ab77c08e50b089a199a5bc8419e1ee6674809c4fb4012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862030047304402206b570b99c22c841548a35a9b9c673fa3b87a9563ed64ad7d979aa3e01b2e303802201d0bebf58b7243e09798e734fc32892936c4d0c4984bec755dc951ef646e4a9a0147512103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d2103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86252ae00000000"
    )

    # Test corrupted signature in witness.
    inp2.witness[10] ^= 1
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_091446),
                request_input(0, TXHASH_091446),
                request_output(0, TXHASH_091446),
                request_output(1, TXHASH_091446),
                request_input(1),
                request_meta(TXHASH_a345b8),
                request_input(0, TXHASH_a345b8),
                request_output(0, TXHASH_a345b8),
                proto.Failure(code=proto.FailureType.DataError),
            ]
        )

        with pytest.raises(TrezorFailure, match="Invalid signature"):
            btc.sign_tx(
                client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_TESTNET
            )


@pytest.mark.skip_t1
def test_p2tr_external_presigned(client):
    inp1 = proto.TxInputType(
        # tb1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq8s8a5u
        address_n=parse_path("86'/1'/0'/0/0"),
        amount=6800,
        prev_hash=TXHASH_df862e,
        prev_index=0,
        script_type=proto.InputScriptType.SPENDTAPROOT,
    )
    inp2 = proto.TxInputType(
        # tb1p8tvmvsvhsee73rhym86wt435qrqm92psfsyhy6a3n5gw455znnpqm8wald
        # m/86'/1'/0'/0/1 for "all all ... all" seed.
        amount=13000,
        prev_hash=TXHASH_3ac32e,
        prev_index=1,
        script_pubkey=bytes.fromhex(
            "51203ad9b641978673e88ee4d9f4e5d63400c1b2a8304c09726bb19d10ead2829cc2"
        ),
        script_type=proto.InputScriptType.EXTERNAL,
        witness=bytearray.fromhex(
            "01409956e47403278bf76eecbbbc3af0c2731d8347763825248a2e0f39aca5a684a7d5054e7222a1033fb5864a886180f1a8c64adab12433c78298d1f83e4c8f46e1"
        ),
    )
    out1 = proto.TxOutputType(
        # 84'/1'/1'/0/0
        address="tb1q7r9yvcdgcl6wmtta58yxf29a8kc96jkyxl7y88",
        amount=15000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )
    out2 = proto.TxOutputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("86'/1'/0'/1/0"),
        script_type=proto.OutputScriptType.PAYTOTAPROOT,
        amount=6800 + 13000 - 200 - 15000,
    )
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                proto.ButtonRequest(code=B.SignTx),
                request_input(1),
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
            client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_TESTNET
        )

    assert (
        serialized_tx.hex()
        == "010000000001029f67664b8972ae01498e25ea98a37889f19aa86a2f39ddad84ff31da312e86df0000000000ffffffff9b117a776a9aaf70d4c3ffe89f009dcd23210a03d649ee5e38791d83902ec33a0100000000ffffffff02983a000000000000160014f0ca4661a8c7f4edad7da1c864a8bd3db05d4ac4f8110000000000002251209a9af24b396f593b34e23fefba6b417a55c5ee3f430c3837379fcb5246ab36d70140b51992353d2f99b7b620c0882cb06694996f1b6c7e62a3c1d3036e0f896fbf0b92f3d9aeab94f2454809a501715667345f702c8214693f469225de5f6636b86b01409956e47403278bf76eecbbbc3af0c2731d8347763825248a2e0f39aca5a684a7d5054e7222a1033fb5864a886180f1a8c64adab12433c78298d1f83e4c8f46e100000000"
    )

    # Test corrupted signature in witness.
    inp2.witness[10] ^= 1
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                proto.ButtonRequest(code=B.SignTx),
                request_input(1),
                proto.Failure(code=proto.FailureType.DataError),
            ]
        )

        with pytest.raises(TrezorFailure, match="Invalid signature"):
            btc.sign_tx(
                client,
                "Testnet",
                [inp1, inp2],
                [out1, out2],
                prev_txes=TX_CACHE_TESTNET,
            )


@pytest.mark.skip_t1
def test_p2pkh_with_proof(client):
    # TODO
    pass


@pytest.mark.skip_t1
def test_p2wpkh_in_p2sh_with_proof(client):
    # TODO
    pass


@pytest.mark.skip_t1
def test_p2wpkh_with_proof(client):
    inp1 = proto.TxInputType(
        # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
        # 84'/1'/0'/0/0
        # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
        amount=100000,
        prev_hash=TXHASH_e5b7e2,
        prev_index=0,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
        ownership_proof=bytearray.fromhex(
            "534c001900016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100d4ad0374c922848c71d913fba59c81b9075e0d33e884d953f0c4b4806b8ffd0c022024740e6717a2b6a5aa03148c3a28b02c713b4e30fc8aeae67fa69eb20e8ddcd9012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
        ),
    )
    inp2 = proto.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=proto.InputScriptType.SPENDWITNESS,
    )
    out1 = proto.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=1230000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )
    out2 = proto.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=100000 + 7289000 - 11000 - 1230000,
        script_type=proto.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
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
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff02b0c4120000000000160014a579388225827d9f2fe9014add644487808c695da0cf5d00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac0002483045022100b17fe0eb21da96bdf9640bbe94f6198ff2ced183765753ee3d5119e661977cb20220121dfdc7a121afdcc08fae1389c7147a10bc58b2daea46799c6e6547c648ba1d012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
    )

    # Test corrupted ownership proof.
    inp1.ownership_proof[10] ^= 1
    with pytest.raises(TrezorFailure, match="Invalid signature"):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )


@pytest.mark.skip_t1
def test_p2wpkh_with_false_proof(client):
    inp1 = proto.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_70f987,
        prev_index=0,
        amount=100000,
        script_type=proto.InputScriptType.SPENDWITNESS,
    )

    inp2 = proto.TxInputType(
        # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
        # address_n=parse_path("m/84h/1h/0h/0/1"),
        prev_hash=TXHASH_65b768,
        prev_index=0,
        amount=10000,
        script_type=proto.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014fb7e49f4017dc951615dea221b66626189aa43b9"),
        ownership_proof=bytes.fromhex(
            "534c00190001b0b66657a824e41c063299fb4435dc70a6fd2e9db4c87e3c26a7ab7c0283547b0002473044022060bf60380142ed54fa907c82cb5ab438bfec22ebf8b5a92971fe104b7e3dd41002206f3fc4ac2f9c1a4a12255b5f678b6e57a088816051faea5a65a66951b394c150012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03"
        ),
    )

    out1 = proto.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=50000,
        script_type=proto.OutputScriptType.PAYTOWITNESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                proto.ButtonRequest(code=B.ConfirmOutput),
                proto.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_70f987),
                request_input(0, TXHASH_70f987),
                request_output(0, TXHASH_70f987),
                request_output(1, TXHASH_70f987),
                request_input(1),
                request_meta(TXHASH_65b768),
                request_input(0, TXHASH_65b768),
                request_output(0, TXHASH_65b768),
                request_output(1, TXHASH_65b768),
                proto.Failure(code=proto.FailureType.DataError),
            ]
        )

        with pytest.raises(TrezorFailure, match="Invalid external input"):
            btc.sign_tx(
                client,
                "Testnet",
                [inp1, inp2],
                [out1],
                prev_txes=TX_CACHE_TESTNET,
            )
