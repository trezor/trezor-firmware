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
from trezorlib.messages import SafetyCheckLevel
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)
TXHASH_d830b8 = bytes.fromhex(
    "d830b877c3d9237a0a68be88825a296da01ac282a2efd2f671d8f17f15117b74"
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
TXHASH_afde2d = bytes.fromhex(
    "afde2d41702948e922150825742cda3294d80d43b8e508865c1e2d648f6d4dae"
)
TXHASH_4012d9 = bytes.fromhex(
    "4012d9abb675243758b8f2cfd0042ce9a6c1459aaf5327dcac16c80f9eff1cbf"
)
TXHASH_1c022d = bytes.fromhex(
    "1c022d9da3aa8bc8cf2a617c42c8f2c343e810af76b3ab9770c5ab6ca54ddab5"
)
TXHASH_ec16dc = bytes.fromhex(
    "ec16dc5a539c5d60001a7471c37dbb0b5294c289c77df8bd07870b30d73e2231"
)
TXHASH_20912f = bytes.fromhex(
    "20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337"
)
TXHASH_1010b2 = bytes.fromhex(
    "1010b25957a30110377a33bd3b0bd39045b3cc488d0e534d1ea5ec238812c0fc"
)


@pytest.mark.skip_t1
def test_p2pkh_presigned(client: Client):
    inp1 = messages.TxInputType(
        # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        amount=31_000_000,
    )

    inp1ext = messages.TxInputType(
        # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        # address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=TXHASH_e5040e,
        prev_index=0,
        amount=31_000_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914a579388225827d9f2fe9014add644487808c695d88ac"
        ),
        script_sig=bytes.fromhex(
            "473044022054fa66bfe1de1c850d59840f165143a66075bae78be3a6bc2809d1ac09431d380220019ecb086e16384f18cbae09b02bd2dce18763cd06454d33d93630561250965e0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        ),
    )

    inp2 = messages.TxInputType(
        # mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b
        address_n=parse_path("m/44h/1h/0h/0/1"),
        prev_hash=TXHASH_d830b8,
        prev_index=1,
        amount=600_000_000,
    )

    inp2ext = messages.TxInputType(
        # mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b
        # address_n=parse_path("m/44h/1h/0h/0/1"),
        prev_hash=TXHASH_d830b8,
        prev_index=1,
        amount=600_000_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a9145b157a678a10021243307e4bb58f36375aa80e1088ac"
        ),
        script_sig=bytearray.fromhex(
            "463043021f3a0a7fdf27b340358ddf8b4e6e3e6cc0be728d6f1d9d3413ae59741f57599002204809d59a9432a2c7fcb10639c5efa82935d8c3cc21b185ff5e44f0e1a80e635401210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852"
        ),
    )

    out1 = messages.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=620_000_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/0"),
        amount=31_000_000 + 600_000_000 - 620_000_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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
def test_p2wpkh_in_p2sh_presigned(client: Client):
    inp1 = messages.TxInputType(
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
        amount=123_456_789,
        prev_hash=TXHASH_20912f,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87"),
        script_sig=bytearray.fromhex("160014d16b8c0680c61fc6ed2e407455715055e41052f5"),
        witness=bytes.fromhex(
            "024830450221009962940c7524c8dee6807d76e0ce1ba4a943604db0bce61357dabe5a4ce2d93a022014fa33769e33eb7e6051d9db28f06cff7ead6c7013839cc26c43f887736a9af1012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b79"
        ),
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_ec16dc,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        # address_n=parse_path("44'/1'/0'/0/0"),
        address="2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=45_600_000,
    )
    out3 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=123_456_789 + 10_000 - 11000 - 12_300_000 - 45_600_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(2),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                request_input(1),
                request_meta(TXHASH_ec16dc),
                request_input(0, TXHASH_ec16dc),
                request_output(0, TXHASH_ec16dc),
                request_output(1, TXHASH_ec16dc),
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

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000000010237c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff31223ed7300b8707bdf87dc789c294520bbb7dc371741a00605d9c535adc16ec0000000000ffffffff03e0aebb0000000000160014a579388225827d9f2fe9014add644487808c695d00cdb7020000000017a91491233e24a9bf8dbb19c1187ad876a9380c12e787874d4de803000000001976a914a579388225827d9f2fe9014add644487808c695d88ac024830450221009962940c7524c8dee6807d76e0ce1ba4a943604db0bce61357dabe5a4ce2d93a022014fa33769e33eb7e6051d9db28f06cff7ead6c7013839cc26c43f887736a9af1012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7902473044022009b2654cd576227c781b14b775df4749d0bcc5661cc39a08b5c42b8ffbc33c5d02203893cc57c46811ec2fb2d27764f3a3b3406040a24d1373cc7f38f79d80dfef1f012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"
    )

    # Test corrupted script hash in scriptsig.
    inp1.script_sig[10] ^= 1
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
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(2),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_20912f),
                request_input(0, TXHASH_20912f),
                request_output(0, TXHASH_20912f),
                request_output(1, TXHASH_20912f),
                messages.Failure(code=messages.FailureType.DataError),
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
def test_p2wpkh_presigned(client: Client):
    inp1 = messages.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_70f987,
        prev_index=0,
        amount=100_000,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    inp2 = messages.TxInputType(
        # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
        # address_n=parse_path("m/84h/1h/0h/0/1"),
        prev_hash=TXHASH_65b768,
        prev_index=0,
        amount=10_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014fb7e49f4017dc951615dea221b66626189aa43b9"),
        script_sig=bytes.fromhex(""),
        witness=bytearray.fromhex(
            "024730440220432ac60461de52713ad543cbb1484f7eca1a72c615d539b3f42f5668da4501d2022063786a6d6940a5c1ed9c2d2fd02cef90b6c01ddd84829c946561e15be6c0aae1012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03"
        ),
    )

    out1 = messages.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=100_000 + 10_000 - 50_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
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

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
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
def test_p2wsh_external_presigned(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_ec16dc,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    inp2 = messages.TxInputType(
        # 1 of 2 multisig
        # m/84'/1'/0' for "alcohol woman abuse ..." seed.
        # m/84'/1'/0' for "all all ... all" seed.
        # tb1qpzmgzpcumztvmpu3q27wwdggqav26j9dgks92pvnne2lz9ferxgssmhzlq
        prev_hash=TXHASH_1c022d,
        prev_index=2,
        amount=100_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "002008b681071cd896cd879102bce735080758ad48ad45a05505939e55f115391991"
        ),
        witness=bytearray.fromhex(
            "03004830450221009c74f5b89440665857f2c775f7c63eb208456aeda12ef9f4ba2c739474f3436202205a069c3bcb31a9fe751818920ae94db4087d432ebd2762741922281d205ac3620147512103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d2103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86252ae"
        ),
    )

    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=10_000 + 100_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_ec16dc),
                request_input(0, TXHASH_ec16dc),
                request_output(0, TXHASH_ec16dc),
                request_output(1, TXHASH_ec16dc),
                request_input(1),
                request_meta(TXHASH_1c022d),
                request_input(0, TXHASH_1c022d),
                request_output(0, TXHASH_1c022d),
                request_output(1, TXHASH_1c022d),
                request_output(2, TXHASH_1c022d),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000000010231223ed7300b8707bdf87dc789c294520bbb7dc371741a00605d9c535adc16ec0000000000ffffffffb5da4da56cabc57097abb376af10e843c3f2c8427c612acfc88baaa39d2d021c0200000000ffffffff01c8a901000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c9870247304402207ec2960e148af81ac1bf570e59a9e17566c9db539826fe6edec622e4378da203022051e4c877ef6ef67700cc9038b9969355f104b608f7b4ed4ee573f3608cc40b69012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86203004830450221009c74f5b89440665857f2c775f7c63eb208456aeda12ef9f4ba2c739474f3436202205a069c3bcb31a9fe751818920ae94db4087d432ebd2762741922281d205ac3620147512103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d2103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86252ae00000000"
    )

    # Test corrupted signature in witness.
    inp2.witness[10] ^= 1
    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_ec16dc),
                request_input(0, TXHASH_ec16dc),
                request_output(0, TXHASH_ec16dc),
                request_output(1, TXHASH_ec16dc),
                request_input(1),
                request_meta(TXHASH_1c022d),
                request_input(0, TXHASH_1c022d),
                request_output(0, TXHASH_1c022d),
                request_output(1, TXHASH_1c022d),
                request_output(2, TXHASH_1c022d),
                messages.Failure(code=messages.FailureType.DataError),
            ]
        )

        with pytest.raises(TrezorFailure, match="Invalid signature"):
            btc.sign_tx(
                client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_TESTNET
            )


@pytest.mark.skip_t1
def test_p2tr_external_presigned(client: Client):
    inp1 = messages.TxInputType(
        # tb1p8tvmvsvhsee73rhym86wt435qrqm92psfsyhy6a3n5gw455znnpqm8wald
        address_n=parse_path("m/86h/1h/0h/0/1"),
        amount=13_000,
        prev_hash=TXHASH_1010b2,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    inp2 = messages.TxInputType(
        # tb1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq8s8a5u
        # m/86h/1h/0h/0/0
        amount=6_800,
        prev_hash=TXHASH_1010b2,
        prev_index=0,
        script_pubkey=bytes.fromhex(
            "512083860592dcc9c672acbca8c23941e85d402b353ce0e099b01dec52a203eff0b6"
        ),
        script_type=messages.InputScriptType.EXTERNAL,
        witness=bytearray.fromhex(
            "0140e241b85650814f35a6a8fe277d8cd784e897b7f032b73cc2f5326dac5991e8f43d54861d624cc119f5409c7d0def65a613691dc17a3700bbc8639a1c8a3184f0"
        ),
    )
    out1 = messages.TxOutputType(
        address="tb1qq0rurzt04d76hk7pjxhqggk7ad4zj7c9u369kt",
        amount=15_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("m/86h/1h/0h/1/0"),
        amount=4_600,
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
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
                messages.ButtonRequest(code=B.SignTx),
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

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/22dee49480bd5a6ee49bdf2dd0c06b49187990bc9a90b2b5f2cdc3567b71690c",
        tx_hex="01000000000102fcc0128823eca51e4d530e8d48ccb34590d30b3bbd337a371001a35759b210100100000000fffffffffcc0128823eca51e4d530e8d48ccb34590d30b3bbd337a371001a35759b210100000000000ffffffff02983a00000000000016001403c7c1896fab7dabdbc191ae0422deeb6a297b05f8110000000000002251209a9af24b396f593b34e23fefba6b417a55c5ee3f430c3837379fcb5246ab36d701405c014bd3cdc94fb1a2d4ead3509fbed1ad3065ad931ea1e998ed29f73212a2506f2ac39a526c237bbf22af75afec64bb9b484b040c72016e30b1337a6274a9ae0140e241b85650814f35a6a8fe277d8cd784e897b7f032b73cc2f5326dac5991e8f43d54861d624cc119f5409c7d0def65a613691dc17a3700bbc8639a1c8a3184f000000000",
    )

    # Test corrupted signature in witness.
    inp2.witness[10] ^= 1
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
                messages.ButtonRequest(code=B.SignTx),
                request_input(1),
                messages.Failure(code=messages.FailureType.DataError),
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
def test_p2pkh_with_proof(client: Client):
    # TODO
    pass


@pytest.mark.skip_t1
def test_p2wpkh_in_p2sh_with_proof(client: Client):
    # TODO
    pass


def test_p2wpkh_with_proof(client: Client):
    inp1 = messages.TxInputType(
        # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
        # 84'/1'/0'/0/0
        # tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2
        amount=100_000,
        prev_hash=TXHASH_e5b7e2,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("00149c02608d469160a92f40fdf8c6ccced029493088"),
        ownership_proof=bytearray.fromhex(
            "534c001900016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c4000247304402201b0a2cd9398f5f3b63e624bb960436a45bdacbd5174b29a47ed3f659b2d4137b022007f8981f476216e012a04956ce77a483cdbff2905227b103a48a15e61379c43d012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d"
        ),
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_ec16dc,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=55_555,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=100_000 + 10_000 - 11000 - 55_555,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_t1 = client.features.model == "1"
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
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_e5b7e2),
                request_input(0, TXHASH_e5b7e2),
                request_output(0, TXHASH_e5b7e2),
                request_output(1, TXHASH_e5b7e2),
                request_input(1),
                request_meta(TXHASH_ec16dc),
                request_input(0, TXHASH_ec16dc),
                request_output(0, TXHASH_ec16dc),
                request_output(1, TXHASH_ec16dc),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                (is_t1, request_input(0)),
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

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff31223ed7300b8707bdf87dc789c294520bbb7dc371741a00605d9c535adc16ec0000000000ffffffff0203d9000000000000160014a579388225827d9f2fe9014add644487808c695db5a90000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000247304402204ab2dfe9eb1268c1cea7d997ae10070c67a26d1c52eb8af06d2e8a4f8befeee30220445294f1568782879c84bf216c80c0f01dc332569c2afd1be5381b0d5a8d6d69012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"
    )

    # Test corrupted ownership proof.
    inp1.ownership_proof[10] ^= 1
    with pytest.raises(TrezorFailure, match="Invalid signature|Invalid external input"):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )


@pytest.mark.setup_client(
    mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
)
def test_p2tr_with_proof(client: Client):
    # Resulting TXID 48ec6dc7bb772ff18cbce0135fedda7c0e85212c7b2f85a5d0cc7a917d77c48a

    inp1 = messages.TxInputType(
        # seed "all all all all all all all all all all all all"
        # 86'/1'/2'/0/0
        # tb1pyu3e8expmey3n5mhra64c9lhz8865rftmaedwa7dddxrlktuv6us6snqxg
        # afde2d41702948e922150825742cda3294d80d43b8e508865c1e2d648f6d4dae
        amount=100_892,
        prev_hash=TXHASH_afde2d,
        prev_index=2,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "5120272393e4c1de4919d3771f755c17f711cfaa0d2bdf72d777cd6b4c3fd97c66b9"
        ),
        ownership_proof=bytearray.fromhex(
            "534c001900015f6c298a141152b5aef9ef31badea5ceaf9f628a968bed0a14d5ad660761cf1c00014022269a1567cb4f892d0702e6be1175de8b892eda26ffde896d2d240814a747e0b574819431c9c8c95c364f15f447019fe3d4dcc6229110d0598f0265af2b5945"
        ),
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/0h/0/0"),
        amount=6_456,
        prev_hash=TXHASH_4012d9,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        address="tb1puyst6yj0x3w5z253k5xt0crk2zjy36g0fzhascd4wknxfwv9h9lszyhefk",
        amount=100_892 + 6_456 - 300,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_t1 = client.features.model == "1"
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_input(1),
                request_output(0),
                (is_t1, request_input(0)),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_TESTNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    # Transaction hex changed with fix #2085, all other details are the same as this tx:
    # https://tbtc1.trezor.io/api/tx/48ec6dc7bb772ff18cbce0135fedda7c0e85212c7b2f85a5d0cc7a917d77c48a
    assert (
        serialized_tx.hex()
        == "01000000000102ae4d6d8f642d1e5c8608e5b8430dd89432da2c7425081522e9482970412ddeaf0200000000ffffffffbf1cff9e0fc816acdc2753af9a45c1a6e92c04d0cff2b858372475b6abd912400000000000ffffffff0128a2010000000000225120e120bd124f345d412a91b50cb7e07650a448e90f48afd861b575a664b985b97f000140b524eaf406d413e19d7d32f7133273728f35b28509ac58dfd817f6dfbbac9901db21cd1ba4c2323c64bede38a7512647369d4767c645a915482bcf5167dcd77100000000"
    )

    # Test corrupted ownership proof.
    inp1.ownership_proof[10] ^= 1
    with pytest.raises(TrezorFailure, match="Invalid signature|Invalid external input"):
        btc.sign_tx(client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_TESTNET)


def test_p2wpkh_with_false_proof(client: Client):
    inp1 = messages.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_70f987,
        prev_index=0,
        amount=100_000,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    inp2 = messages.TxInputType(
        # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
        # address_n=parse_path("m/84h/1h/0h/0/1"),
        prev_hash=TXHASH_65b768,
        prev_index=0,
        amount=10_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014fb7e49f4017dc951615dea221b66626189aa43b9"),
        ownership_proof=bytes.fromhex(
            "534c00190001b0b66657a824e41c063299fb4435dc70a6fd2e9db4c87e3c26a7ab7c0283547b000247304402206e285291aa955cb60b16acd69332eaada67ec5192d361fe4e2b384553e7e80c6022023470cfcb9c3251a136c26eb1637142206785a3d91b98583e5a1d6ab64fa91ed012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03"
        ),
    )

    out1 = messages.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                messages.Failure(code=messages.FailureType.DataError),
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


def test_p2tr_external_unverified(client: Client):
    inp1 = messages.TxInputType(
        # tb1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq8s8a5u
        address_n=parse_path("m/86h/1h/0h/0/0"),
        amount=6_800,
        prev_hash=TXHASH_df862e,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    inp2 = messages.TxInputType(
        # tb1p8tvmvsvhsee73rhym86wt435qrqm92psfsyhy6a3n5gw455znnpqm8wald
        # m/86'/1'/0'/0/1 for "all all ... all" seed.
        amount=13_000,
        prev_hash=TXHASH_3ac32e,
        prev_index=1,
        script_pubkey=bytes.fromhex(
            "51203ad9b641978673e88ee4d9f4e5d63400c1b2a8304c09726bb19d10ead2829cc2"
        ),
        script_type=messages.InputScriptType.EXTERNAL,
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

    # Unverified external inputs should be rejected when safety checks are enabled.
    with pytest.raises(TrezorFailure, match="[Ee]xternal input"):
        btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_TESTNET
        )

    # Signing should succeed after disabling safety checks.
    device.apply_settings(client, safety_checks=SafetyCheckLevel.PromptTemporarily)
    _, serialized_tx = btc.sign_tx(
        client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_TESTNET
    )

    # Second witness is missing from the serialized transaction.
    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001029f67664b8972ae01498e25ea98a37889f19aa86a2f39ddad84ff31da312e86df0000000000ffffffff9b117a776a9aaf70d4c3ffe89f009dcd23210a03d649ee5e38791d83902ec33a0100000000ffffffff02983a000000000000160014f0ca4661a8c7f4edad7da1c864a8bd3db05d4ac4f8110000000000002251209a9af24b396f593b34e23fefba6b417a55c5ee3f430c3837379fcb5246ab36d70140496fddbbddff45c7006d56c96fc9f2d6b5c785d7ca8f09230b944e2d2f07452610191bdbc3d6f625d5a0a0b04e49d85427df8a5bb033b3156541abef66e66aba0000000000"
    )


def test_p2wpkh_external_unverified(client: Client):
    inp1 = messages.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        prev_hash=TXHASH_70f987,
        prev_index=0,
        amount=100_000,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    inp2 = messages.TxInputType(
        # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
        # address_n=parse_path("m/84h/1h/0h/0/1"),
        prev_hash=TXHASH_65b768,
        prev_index=0,
        amount=10_000,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014fb7e49f4017dc951615dea221b66626189aa43b9"),
    )

    out1 = messages.TxOutputType(
        address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=100_000 + 10_000 - 50_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    # Unverified external inputs should be rejected when safety checks are enabled.
    with pytest.raises(TrezorFailure, match="[Ee]xternal input"):
        btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_TESTNET
        )

    # Signing should succeed after disabling safety checks.
    device.apply_settings(client, safety_checks=SafetyCheckLevel.PromptTemporarily)
    _, serialized_tx = btc.sign_tx(
        client, "Testnet", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_TESTNET
    )

    # Second witness is missing from the serialized transaction.
    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001029e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700000000000ffffffffd9375b60919f9d5e1db4d7c6aba3d61d4fa080fba195bdee09b2cfccda68b7650000000000ffffffff0250c30000000000001600149c02608d469160a92f40fdf8c6ccced02949308878e6000000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b0247304402207be75627767e59046da2699328ca1c27b60cfb34bb257a9d90442e496b5f936202201f43e2b55e1b2acf5677d3e29b9c5a78e2a4ae03a01be5c50a17cf4b88a3b278012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f8620000000000"
    )
