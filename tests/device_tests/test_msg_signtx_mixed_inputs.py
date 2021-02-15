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
from trezorlib.tools import parse_path

from ..tx_cache import TxCache

TX_API = TxCache("Testnet")

TXHASH_2bac7a = bytes.fromhex(
    "2bac7ad1dec654579a71ea9555463f63ac7b7df9d8ba67b4682bba4e514d0f0c"
)
TXHASH_65b811 = bytes.fromhex(
    "65b811d3eca0fe6915d9f2d77c86c5a7f19bf66b1b1253c2c51cb4ae5f0c017b"
)
TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)
TXHASH_31bc1c = bytes.fromhex(
    "31bc1c88ce6ae337a6b3057a16d5bad0b561ad1dfc047d0a7fbb8814668f91e5"
)


@pytest.mark.skip_ui
def test_non_segwit_segwit_inputs(client):
    # First is non-segwit, second is segwit.

    inp1 = messages.TxInputType(
        address_n=parse_path("44'/1'/0'/0/0"),
        amount=31000000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=31000000 + 7289000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        signatures, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 2
    assert (
        signatures[0].hex()
        == "3045022100b9b1002dfaa8aa6e658e37726dc526f145bac3715a933d40f8dacadff2cede560220197691c6bfc55ff260f5a48e9e94d9db73aff0400d79600f8ca63b7c0c7b3701"
    )
    assert (
        signatures[1].hex()
        == "3044022013dd59fb2e22da981a528b155e25e3ce360001c275408ea649b34cd51b509e68022030febb79bbb3e75263cdb68d9b9e08ab0ebe85d1986eb4fa5ce2f668b40a2a2c"
    )
    assert (
        serialized_tx.hex()
        == "01000000000102cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100b9b1002dfaa8aa6e658e37726dc526f145bac3715a933d40f8dacadff2cede560220197691c6bfc55ff260f5a48e9e94d9db73aff0400d79600f8ca63b7c0c7b37010121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff01803a480200000000160014a579388225827d9f2fe9014add644487808c695d0002473044022013dd59fb2e22da981a528b155e25e3ce360001c275408ea649b34cd51b509e68022030febb79bbb3e75263cdb68d9b9e08ab0ebe85d1986eb4fa5ce2f668b40a2a2c012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000"
    )


@pytest.mark.skip_ui
def test_segwit_non_segwit_inputs(client):
    # First is segwit, second is non-segwit.

    inp1 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("44'/1'/0'/0/0"),
        amount=31000000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=31000000 + 7289000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        signatures, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 2
    assert (
        signatures[0].hex()
        == "3045022100d9bde6725e682080bfdb4fca6cf839999cd149aeac06c98983a65ec3576440880220692c7385c528ecb3780aadd85c900a4631cab88ec1db5d08391702f75aa3ddd6"
    )
    assert (
        signatures[1].hex()
        == "3045022100e485b07ec517994a436c631966060aeddc7f34acf8e818b8262de8686bfbbb04022030f04f4facab8e4a21f9849dcdfc86cd781faec98e782b4a137ca8b20c88f98d"
    )
    assert (
        serialized_tx.hex()
        == "010000000001027b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffffcd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100e485b07ec517994a436c631966060aeddc7f34acf8e818b8262de8686bfbbb04022030f04f4facab8e4a21f9849dcdfc86cd781faec98e782b4a137ca8b20c88f98d0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff01803a480200000000160014a579388225827d9f2fe9014add644487808c695d02483045022100d9bde6725e682080bfdb4fca6cf839999cd149aeac06c98983a65ec3576440880220692c7385c528ecb3780aadd85c900a4631cab88ec1db5d08391702f75aa3ddd6012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0000000000"
    )


@pytest.mark.skip_ui
def test_segwit_non_segwit_segwit_inputs(client):
    # First is segwit, second is non-segwit and third is segwit again.

    inp1 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("44'/1'/0'/0/0"),
        amount=31000000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )
    inp3 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=1603000,
        prev_hash=TXHASH_31bc1c,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=31000000 + 7289000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        signatures, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2, inp3], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 3
    assert (
        signatures[0].hex()
        == "3044022001187697b2ae95206eb18751701b6a3efd4c2da89cc9d8f0365e8ede7582c8ff0220282a2c127da57e82aecf0f421f7b8d5781205232b3429dd25d2b85aa1e48b741"
    )
    assert (
        signatures[1].hex()
        == "30440220566602a3794e29a5082feb2efd9ce0299455d0c4a31f76d4abafdcc0fed1cde502200ae36cb0563cf4792fd8a10026ec7c94028ca61a5b6903108af3343278ad29bb"
    )
    assert (
        signatures[2].hex()
        == "3045022100f2d398ac6bc702cfa4f7eb3d2579a233f1d7c920c45a14329a741db6c24fde8f02203b1f6aed5671eece8ba5b5c05ec0330a43c0914b8ff606945cb8cf9e164ec88f"
    )
    assert (
        serialized_tx.hex()
        == "010000000001037b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffffcd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006a4730440220566602a3794e29a5082feb2efd9ce0299455d0c4a31f76d4abafdcc0fed1cde502200ae36cb0563cf4792fd8a10026ec7c94028ca61a5b6903108af3343278ad29bb0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffffe5918f661488bb7f0a7d04fc1dad61b5d0bad5167a05b3a637e36ace881cbc310000000000ffffffff01803a480200000000160014a579388225827d9f2fe9014add644487808c695d02473044022001187697b2ae95206eb18751701b6a3efd4c2da89cc9d8f0365e8ede7582c8ff0220282a2c127da57e82aecf0f421f7b8d5781205232b3429dd25d2b85aa1e48b741012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0002483045022100f2d398ac6bc702cfa4f7eb3d2579a233f1d7c920c45a14329a741db6c24fde8f02203b1f6aed5671eece8ba5b5c05ec0330a43c0914b8ff606945cb8cf9e164ec88f012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"
    )


@pytest.mark.skip_ui
def test_non_segwit_segwit_non_segwit_inputs(client):
    # First is non-segwit, second is segwit and third is non-segwit again.

    inp1 = messages.TxInputType(
        address_n=parse_path("44'/1'/0'/0/0"),
        amount=31000000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        amount=7289000,
        prev_hash=TXHASH_65b811,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp3 = messages.TxInputType(
        address_n=parse_path("44'/1'/1'/0/0"),
        amount=9226912,
        prev_hash=TXHASH_2bac7a,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=31000000 + 7289000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        signatures, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1, inp2, inp3], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 3
    assert (
        signatures[0].hex()
        == "3045022100c9d0bad841a085b469c85794291989b6cd902f98abd5e0c6cab02f36461e4a3d022031298c4a1c36aa87abcf58f1f0991bba0afca98af8acf1dca73cd922cd85fccf"
    )
    assert (
        signatures[1].hex()
        == "30440220164615767205a8fd7acf924a224c4c01476a5e545cd9033eba7d63dc4b4e200b02201cbf837c8e98014e7170568546f430bb8e3d7e3071fe53e7cff20a7b90778553"
    )
    assert (
        signatures[2].hex()
        == "3045022100baebd59a19048836ac733a177935bb093214fa106d192952d6651e989b634c620220708355edb1ca0e96f6ba1c6db3a84a5c960905db044443b038f70206427d889e"
    )
    assert (
        serialized_tx.hex()
        == "01000000000103cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100c9d0bad841a085b469c85794291989b6cd902f98abd5e0c6cab02f36461e4a3d022031298c4a1c36aa87abcf58f1f0991bba0afca98af8acf1dca73cd922cd85fccf0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff0c0f4d514eba2b68b467bad8f97d7bac633f465595ea719a5754c6ded17aac2b000000006b483045022100baebd59a19048836ac733a177935bb093214fa106d192952d6651e989b634c620220708355edb1ca0e96f6ba1c6db3a84a5c960905db044443b038f70206427d889e012103bae960983f83e28fcb8f0e5f3dc1f1297b9f9636612fd0835b768e1b7275fb9dffffffff01803a480200000000160014a579388225827d9f2fe9014add644487808c695d00024730440220164615767205a8fd7acf924a224c4c01476a5e545cd9033eba7d63dc4b4e200b02201cbf837c8e98014e7170568546f430bb8e3d7e3071fe53e7cff20a7b90778553012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0000000000"
    )
