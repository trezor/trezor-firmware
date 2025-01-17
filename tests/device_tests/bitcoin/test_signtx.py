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

from datetime import datetime, timezone

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import H_, parse_path

from ...common import is_core
from ...input_flows import (
    InputFlowLockTimeBlockHeight,
    InputFlowLockTimeDatetime,
    InputFlowSignTxHighFee,
    InputFlowSignTxInformation,
    InputFlowSignTxInformationCancel,
    InputFlowSignTxInformationMixed,
    InputFlowSignTxInformationReplacement,
)
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

TXHASH_157041 = bytes.fromhex(
    "1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)
FAKE_TXHASH_005f6f = bytes.fromhex(  # FAKE transaction (coinbase)
    "005f6f7ff4b70aa09a15b3bc36607d378fad104c4efa4f0a1c8e970538622b3e"
)
TXHASH_d2dcda = bytes.fromhex(
    "d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24"
)
TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)
TXHASH_ec5194 = bytes.fromhex(
    "ec519494bea3746bd5fbdd7a15dac5049a873fa674c67e596d46505b9b835425"
)
TXHASH_50f6f1 = bytes.fromhex(
    "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
)
TXHASH_2bac7a = bytes.fromhex(
    "2bac7ad1dec654579a71ea9555463f63ac7b7df9d8ba67b4682bba4e514d0f0c"
)
TXHASH_bb5169 = bytes.fromhex(
    "bb5169091f09e833e155b291b662019df56870effe388c626221c5ea84274bc4"
)
TXHASH_0dac36 = bytes.fromhex(
    "0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5"
)
TXHASH_ac4ca0 = bytes.fromhex(
    "ac4ca0e7827a1228f44449cb57b4b9a809a667ca044dc43bb124627fed4bc10a"
)
TXHASH_58d56a = bytes.fromhex(
    "58d56a5d1325cf83543ee4c87fd73a784e4ba1499ced574be359fa2bdcb9ac8e"
)
TXHASH_301948 = bytes.fromhex(
    "3019487f064329247daad245aed7a75349d09c14b1d24f170947690e030f5b20"
)
TXHASH_892d06 = bytes.fromhex(
    "892d06cb3394b8e6006eec9a2aa90692b718a29be6844b6c6a9e89ec3aa6aac4"
)
TXHASH_074b00 = bytes.fromhex(
    "074b0070939db4c2635c1bef0c8e68412ccc8d3c8782137547c7a2bbde073fc0"
)
TXHASH_25fee5 = bytes.fromhex(
    "25fee583181847cbe9d9fd9a483a8b8626c99854a72d01de848ef40508d0f3bc"
)
TXHASH_1f326f = bytes.fromhex(
    "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
)
TXHASH_334cd7 = bytes.fromhex(
    "334cd7ad982b3b15d07dd1c84e939e95efb0803071648048a7f289492e7b4c8a"
)
TXHASH_5e7667 = bytes.fromhex(
    "5e7667690076ae4737e2f872005de6f6b57592f32108ed9b301eeece6de24ad6"
)
TXHASH_efaa41 = bytes.fromhex(
    "efaa41ff3e67edf508846c1a1ed56894cfd32725c590300108f40c9edc1aac35"
)

CORNER_BUTTON = (215, 25)


def test_one_one_fee(client: Client):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
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
                request_meta(TXHASH_0dac36),
                request_input(0, TXHASH_0dac36),
                request_output(0, TXHASH_0dac36),
                request_output(1, TXHASH_0dac36),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b893aeed4b12227b6f5348d7f6cb84ba2cda2ba70a41933a25f363b9d2fc2cf9",
        tx_hex="0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100dd4dd136a70371bc9884c3c51fd52f4aed9ab8ee98f3ac7367bb19e6538096e702200c56be09c4359fc7eb494b4bdf8f2b72706b0575c4021373345b593e9661c7b6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0148c40000000000001976a91419140511436e947448be994ab7fda9f98623e68e88ac00000000",
    )


def test_testnet_one_two_fee(client: Client):
    # input tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",  # looks like an old faucet
        amount=30_090_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/0"),  # mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ
        amount=900_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_e5040e),
                request_input(0, TXHASH_e5040e),
                request_output(0, TXHASH_e5040e),
                request_output(1, TXHASH_e5040e),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56",
        tx_hex="0100000001cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100eba3bbcbb82ab1ebac88a394e8fb53b0263dadbb3e8072f0a21ee62818c911060220686a9b7f306d028b54a228b5c47cc6c27b1d01a3b0770440bcc64d55d8bace2c0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff021023cb01000000001976a91485eb47fe98f349065d6f044e27a4ac541af79ee288aca0bb0d00000000001976a9143d3cca567e00a04819742b21a696a67da796498b88ac00000000",
    )


def test_testnet_fee_high_warning(client: Client):
    # input tx: 25fee583181847cbe9d9fd9a483a8b8626c99854a72d01de848ef40508d0f3bc
    # (The "25fee" tx hash is very suitable for testing high fees)

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=129_999_808,
        prev_hash=TXHASH_25fee5,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",  # "m/44h/1h/0h/0/6"
        amount=129_999_808 - 2_500_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.FeeOverThreshold),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_25fee5),
                request_input(0, TXHASH_25fee5),
                request_output(0, TXHASH_25fee5),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000001bcf3d00805f48e84de012da75498c926868b3a489afdd9e9cb47181883e5fe25000000006a47304402201602fd17c6e1d8c785ce150d6c0ec97f8a93fb71f6294f3a1de7dd52a52e27fe022079c05bc14f7b94771d195cb330a4dd7c0765290c6e183ae6aa169e4d5ccf2a3a0121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffff01207e9907000000001976a9144cfc772f24b600762f905a1ee799ce0e9c26831f88ac00000000"
    )


def test_one_two_fee(client: Client):
    # input tx: 50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/5"),  # 1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ
        amount=50_000,
        prev_hash=TXHASH_50f6f1,
        prev_index=1,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/3"),  # 1EcL6AyfQTyWKGvXwNSfsWoYnD3whzVFdu
        amount=30_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1Up15Msx4sbvUCGm8Xgo2Zp5FQim3wE59",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_50f6f1),
                request_input(0, TXHASH_50f6f1),
                request_output(0, TXHASH_50f6f1),
                request_output(1, TXHASH_50f6f1),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1, out2], prev_txes=TX_CACHE_MAINNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/c275c333fd1b36bef4af316226c66a8b3693fbfcc081a5e16a2ae5fcb09e92bf",
        tx_hex="01000000016d20f69067ad1ffd50ee7c0f377dde2c932ccb03e84b5659732da99c20f1f650010000006a47304402203429bd3ce7b38c5c1e8a15340edd79ced41a2939aae62e259d2e3d18e0c5ee7602201b83b10ebc4d6dcee3f9eb42ba8f1ef8a059a05397e0c1b9223d1565a3e6ec01012102a7a079c1ef9916b289c2ff21a992c808d0de3dfcf8a9f163205c5c9e21f55d5cffffffff0230750000000000001976a914954820f1de627a703596ac0396f986d958e3de4c88ac10270000000000001976a91405427736705cfbfaff76b1cff48283707fb1037088ac00000000",
    )


@pytest.mark.parametrize("chunkify", (True, False))
def test_one_three_fee(client: Client, chunkify: bool):
    # input tx: bb5169091f09e833e155b291b662019df56870effe388c626221c5ea84274bc4

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/1h/0/21"),  # mvukVu96xM1QJ971w4Z5cdX4tsJwDyQy2L
        amount=1_183_825,
        prev_hash=TXHASH_bb5169,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="mgCyjvJaTgVwKoxEaFaDLeFQpZc7qdKXpZ",  # m/44h/1h/1h/0/20
        amount=100_100,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="n4qJziM7S8ydGbXKKRJADHuSeAjbx5c1Dp",  # m/44h/1h/1h/0/22
        amount=100_100,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out3 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/1h/1/21"),  # n1CFre3Ai975UiWJrjZnFxTVrPkxCVkm8U
        amount=1_183_825 - 100_100 - 100_100 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(2),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_bb5169),
                request_input(0, TXHASH_bb5169),
                request_output(0, TXHASH_bb5169),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(0),
                request_output(1),
                request_output(2),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out2, out3],
            prev_txes=TX_CACHE_TESTNET,
            chunkify=chunkify,
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/tx/29f83be103368bb2302953f5bf57e7eb44f79e46a38c8cd9e862e81ed0fbf0c7",
        tx_hex="0100000001c44b2784eac52162628c38feef7068f59d0162b691b255e133e8091f096951bb000000006b483045022100d9d870e818bf892b76bcb0e68368ce2a1854526e02b8f8b9a480a2bd6f30c6c302204f771373744d00bd7320237878446e5567cb2359db5fbd6a46d35e37a98b16c0012102eee6b3ec6435f42ca071707eb1b14647d2121e0f8a53fa7fa9f92a691227a3d9ffffffff0304870100000000001976a9140791d872b21bf1ae4d7bda4a5c16edefa0b5754488ac04870100000000001976a914ffc3a922d44ced4fcf40df09479e36ee136ec44a88ac39db0e00000000001976a914d7d945b35976a9dbf3f16f2243b5d3da1965538988ac00000000",
    )


def test_two_two(client: Client):
    # input tx: ac4ca0e7827a1228f44449cb57b4b9a809a667ca044dc43bb124627fed4bc10a

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/55"),  # 14nw9rFTWGUncHZjSqpPSJQaptWW7iRRB8
        amount=10_000,
        prev_hash=TXHASH_ac4ca0,
        prev_index=1,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/1/7"),  # 16hgR6bjr99X6NhrsWuDR6NLpCLEacUNk
        amount=83_130,
        prev_hash=TXHASH_ac4ca0,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/8"),  # 1CJzc38F82zBUnMKWxeUqMepkPRmo2BGHt
        amount=71_790,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1ByqmhXkC6U5GuUNnAhJsuEVjHt5GhEuJL",  # m/44h/0h/1h/0/17
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_ac4ca0),
                request_input(0, TXHASH_ac4ca0),
                request_output(0, TXHASH_ac4ca0),
                request_output(1, TXHASH_ac4ca0),
                request_input(1),
                request_meta(TXHASH_ac4ca0),
                request_input(0, TXHASH_ac4ca0),
                request_output(0, TXHASH_ac4ca0),
                request_output(1, TXHASH_ac4ca0),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_MAINNET,
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b928870bf5cd1915ded2cfdc562bf777476860030b8b0bc7beeffa3585457ea9",
        tx_hex="01000000020ac14bed7f6224b13bc44d04ca67a609a8b9b457cb4944f428127a82e7a04cac010000006b483045022100c6dea23b4f43b7aa9ee1b1bb73da8b5e0f16a1160bf0ff1b0493fc7f5d52d79702202dd70a38530ba8ac16f8f5fceab593574241593c8368c27e63325c77417f4a5b01210352b08794e4ac7c33ffa00772e6d1ac6495ec1ffec6f94e76810d6d758749cb0dffffffff0ac14bed7f6224b13bc44d04ca67a609a8b9b457cb4944f428127a82e7a04cac000000006a4730440220050a20fb7d2d5ab57b730fe9f39c3dfe56bd368e38309a41aeb739831dd75e1e02205cfc7608b08dd7236641851a648573623e53b4cbcdbc2a7fbcb0e1f5d067a6e3012102f4c0b068cb14b4d8264097c9ebf262cee4b3e70cf078b49fb29b37cd1d90e6bbffffffff026e180100000000001976a9147c108a5a090dcf88c0df6a6fe1a846ee3193972d88ac10270000000000001976a9147871436e524916ac9faed014a181b20d74723bb588ac00000000",
    )


@pytest.mark.slow
def test_lots_of_inputs(client: Client):
    # Tests if device implements serialization of len(inputs) correctly

    # input tx: 3019487f064329247daad245aed7a75349d09c14b1d24f170947690e030f5b20

    inputs = []
    for i in range(100):
        inputs.append(
            messages.TxInputType(
                address_n=parse_path(f"m/44h/1h/1h/0/{i}"),
                amount=14_598,
                prev_hash=TXHASH_301948,
                prev_index=i,
            )
        )
    out = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",  # "m/44h/1h/0h/0/6"
        amount=100 * 14_598 - 60_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Testnet", inputs, [out], prev_txes=TX_CACHE_TESTNET
    )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/3df8a9d28adb1653fdd98f5a71c82c52fea9389d71b73f3ef7a36a53591cbeda",
    )


@pytest.mark.slow
def test_lots_of_outputs(client: Client):
    # Tests if device implements serialization of len(outputs) correctly

    # input tx: 58d56a5d1325cf83543ee4c87fd73a784e4ba1499ced574be359fa2bdcb9ac8e

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=1_827_955,
        prev_hash=TXHASH_58d56a,
        prev_index=1,
    )

    outputs = []
    cnt = 255
    for _ in range(cnt):
        out = messages.TxOutputType(
            address="momtnzR3XqXgDSsFmd8gkGxUiHZLde3RmA",  # "m/44h/1h/0h/0/3"
            amount=(1_827_955 - 10_000) // cnt,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
        outputs.append(out)

    _, serialized_tx = btc.sign_tx(
        client, "Testnet", [inp1], outputs, prev_txes=TX_CACHE_TESTNET
    )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/f9509e192651732a1a144aa44edd709fd6f1812ffa3dfa72d737cbd8477230c1",
    )


@pytest.mark.slow
def test_lots_of_change(client: Client):
    # Tests if device implements prompting for multiple change addresses correctly

    # input tx: 892d06cb3394b8e6006eec9a2aa90692b718a29be6844b6c6a9e89ec3aa6aac4

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/6"),  # mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs
        amount=1_553_800,
        prev_hash=TXHASH_892d06,
        prev_index=0,
    )

    outputs = [
        messages.TxOutputType(
            address="mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG",  # "m/44h/1h/0h/0/7"
            amount=500_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
    ]

    cnt = 20
    for i in range(cnt):
        out = messages.TxOutputType(
            address_n=parse_path(f"m/44h/1h/0h/1/{i}"),
            amount=(1_553_800 - 500_000 - 29_000) // cnt,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
        outputs.append(out)

    request_change_outputs = [request_output(i + 1) for i in range(cnt)]

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
            ]
            + request_change_outputs
            + [
                messages.ButtonRequest(code=B.SignTx),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_892d06),
                request_input(0, TXHASH_892d06),
                request_output(0, TXHASH_892d06),
                request_input(0),
                request_output(0),
            ]
            + request_change_outputs
            + [request_output(0)]
            + request_change_outputs
            + [request_finished()]
        )

        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], outputs, prev_txes=TX_CACHE_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/15508224d220a4d5dfc202d8722a662b8a3b77b7265d7bea973e10e95b20cead",
    )


def test_fee_high_warning(client: Client):
    # input tx: 1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/10"),  # 1JL3nCw76rhwK6EguU6uhe7GCa7Mq88kXg
        amount=3_801_747,
        prev_hash=TXHASH_1f326f,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1DXKPgQU6ACQiww48chz7iPJhoV5L5bjRC",  # m/44h/0h/0h/0/11
        amount=3_801_747 - 510_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.FeeOverThreshold),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_1f326f),
                request_input(0, TXHASH_1f326f),
                request_input(1, TXHASH_1f326f),
                request_output(0, TXHASH_1f326f),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000001f36ea247c36f027a45d0265718c74ae8ab87bd45b3fb6e14ef558d76656f321f000000006a4730440220342860add2f161c74a67462cd209783557ab5affafe12fa53436a924eb2b2bcb022032be926c63df8532464e9e4adf0cf8f4609f959e230c58fdf306302f3b7fa60a0121038bac33bcdaeec5626e2f2c5680a9fdc5e551d4e1167f272825bea98e6158d4c8ffffffff01633a3200000000001976a914895d571ebb79808367bfd2a70742ac08f519cb6088ac00000000"
    )


@pytest.mark.models("core")
def test_fee_high_hardfail(client: Client):
    # input tx: 25fee583181847cbe9d9fd9a483a8b8626c99854a72d01de848ef40508d0f3bc
    # (The "25fee" tx hash is very suitable for testing high fees)

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=129_999_808,
        prev_hash=TXHASH_25fee5,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",  # "m/44h/1h/0h/0/6"
        amount=129_999_808 - 25_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure, match="fee is unexpectedly large"):
        btc.sign_tx(client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET)

    # set SafetyCheckLevel to PromptTemporarily and try again
    device.apply_settings(
        client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )
    with client:
        IF = InputFlowSignTxHighFee(client)
        client.set_input_flow(IF.get())

        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
        )
        assert IF.finished

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000001bcf3d00805f48e84de012da75498c926868b3a489afdd9e9cb47181883e5fe25000000006a473044022005935c56d59c78e874c1d0556e1a131677214c75a57e8477b44b24ca35e3d5850220281f5d79c6583b528eaf0611904674d9895a3cea0dffd840bafa9d4f67627b200121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffff01802b4206000000001976a9144cfc772f24b600762f905a1ee799ce0e9c26831f88ac00000000"
    )


def test_not_enough_funds(client: Client):
    # input tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),  # 1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL
        amount=390_000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=400_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.Failure(code=messages.FailureType.NotEnoughFunds),
            ]
        )
        with pytest.raises(TrezorFailure, match="NotEnoughFunds"):
            btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)


def test_p2sh(client: Client):
    # input tx: 58d56a5d1325cf83543ee4c87fd73a784e4ba1499ced574be359fa2bdcb9ac8e

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/2"),  # mgswWyysmViMqYmn5XEj1pVz7rVUftVEBP
        amount=50_000,
        prev_hash=TXHASH_58d56a,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="2N4sUHkkx1GgWtMMgjVD5Ljw2yDs7GumT2S",  # p2sh
        amount=50_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOSCRIPTHASH,
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
                request_meta(TXHASH_58d56a),
                request_input(0, TXHASH_58d56a),
                request_output(0, TXHASH_58d56a),
                request_output(1, TXHASH_58d56a),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/525693745ef44161ed32f3def7f13e92d96504e06448910ce2e945bfe5e8cc7b",
        tx_hex="01000000018eacb9dc2bfa59e34b57ed9c49a14b4e783ad77fc8e43e5483cf25135d6ad558000000006a473044022029b7d07f068501dc7a5dcf5148167a286a949483cac88b6f85b3ae92baa3346902203488709587453467248d52d0f18fa36d43909854ee1958feef5c9b78c509d15d012103f5008445568548bd745a3dedccc6048969436bf1a49411f60938ff1938941f14ffffffff01409c00000000000017a9147f844bdb0b8fd54b64e3d16c85dc1170f1ff97c18700000000",
    )


def test_testnet_big_amount(client: Client):
    # This test is testing transaction with amount bigger than fits to uint32

    # input tx: 074b0070939db4c2635c1bef0c8e68412ccc8d3c8782137547c7a2bbde073fc0

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/6"),  # mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs
        amount=4_500_000_000,
        prev_hash=TXHASH_074b00,
        prev_index=1,
    )
    out1 = messages.TxOutputType(
        address="2N5daLhptwpXPBY84TQ2AjeLLkL8ru7n6ai",  # top secret address
        amount=4_500_000_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
    )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/890155c89905c86fb087eddbe9973fa845c99913836e872f41fbdfa3864b607d",
        tx_hex="0100000001c03f07debba2c747751382873c8dcc2c41688e0cef1b5c63c2b49d9370004b07010000006b483045022100a2c79eaed632746fd514aa09eae51c0294bdf66c74619306e0273cd1a470c9e7022050c78dec6acd65b42150dba70e2b546dfd737d77f46975a97427999cb2b8280401210344e14b3da8f5fe77a5465d0f8fe089d64ed5517d1f1f989edd00f530938a2c22ffffffff01f065380c0100000017a91487dba64df7e9386d0b0f3ef557269833e12d1b7a8700000000",
    )


def test_attack_change_outputs(client: Client):
    # input tx: ac4ca0e7827a1228f44449cb57b4b9a809a667ca044dc43bb124627fed4bc10a

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/55"),  # 14nw9rFTWGUncHZjSqpPSJQaptWW7iRRB8
        amount=10_000,
        prev_hash=TXHASH_ac4ca0,
        prev_index=1,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/1/7"),  # 16hgR6bjr99X6NhrsWuDR6NLpCLEacUNk
        amount=83_130,
        prev_hash=TXHASH_ac4ca0,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/8"),  # 1CJzc38F82zBUnMKWxeUqMepkPRmo2BGHt
        amount=71_790,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1ByqmhXkC6U5GuUNnAhJsuEVjHt5GhEuJL",  # m/44h/0h/1h/0/17
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # Test if the transaction can be signed normally
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_ac4ca0),
                request_input(0, TXHASH_ac4ca0),
                request_output(0, TXHASH_ac4ca0),
                request_output(1, TXHASH_ac4ca0),
                request_input(1),
                request_meta(TXHASH_ac4ca0),
                request_input(0, TXHASH_ac4ca0),
                request_output(0, TXHASH_ac4ca0),
                request_output(1, TXHASH_ac4ca0),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_MAINNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b928870bf5cd1915ded2cfdc562bf777476860030b8b0bc7beeffa3585457ea9",
        tx_hex="01000000020ac14bed7f6224b13bc44d04ca67a609a8b9b457cb4944f428127a82e7a04cac010000006b483045022100c6dea23b4f43b7aa9ee1b1bb73da8b5e0f16a1160bf0ff1b0493fc7f5d52d79702202dd70a38530ba8ac16f8f5fceab593574241593c8368c27e63325c77417f4a5b01210352b08794e4ac7c33ffa00772e6d1ac6495ec1ffec6f94e76810d6d758749cb0dffffffff0ac14bed7f6224b13bc44d04ca67a609a8b9b457cb4944f428127a82e7a04cac000000006a4730440220050a20fb7d2d5ab57b730fe9f39c3dfe56bd368e38309a41aeb739831dd75e1e02205cfc7608b08dd7236641851a648573623e53b4cbcdbc2a7fbcb0e1f5d067a6e3012102f4c0b068cb14b4d8264097c9ebf262cee4b3e70cf078b49fb29b37cd1d90e6bbffffffff026e180100000000001976a9147c108a5a090dcf88c0df6a6fe1a846ee3193972d88ac10270000000000001976a9147871436e524916ac9faed014a181b20d74723bb588ac00000000",
    )

    run_attack = False

    def attack_processor(msg):
        nonlocal run_attack
        if msg.tx.outputs and msg.tx.outputs[0] == out2:
            if not run_attack:
                run_attack = True
            else:
                # Sign output with another amount
                msg.tx.outputs[0].amount = 9_999_999

        return msg

    with client, pytest.raises(
        TrezorFailure, match="Transaction has changed during signing"
    ):
        # Set up attack processors
        client.set_filter(messages.TxAck, attack_processor)

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1, inp2],
            [out1, out2],
            prev_txes=TX_CACHE_MAINNET,
        )


def test_attack_modify_change_address(client: Client):
    # Ensure that if the change output is modified after the user confirms the
    # transaction, then signing fails.

    # input tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
    # output tx 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",  # looks like an old faucet
        amount=30_090_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/0"),  # mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ
        amount=900_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    run_attack = False

    def attack_processor(msg):
        nonlocal run_attack
        if msg.tx.outputs and msg.tx.outputs[0] == out2:
            if not run_attack:
                run_attack = True
            else:
                msg.tx.outputs[0].address_n = []
                # 44h/1h/4h/0/2
                msg.tx.outputs[0].address = "mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY"

        return msg

    with client, pytest.raises(
        TrezorFailure, match="Transaction has changed during signing"
    ):
        # Set up attack processors
        client.set_filter(messages.TxAck, attack_processor)

        btc.sign_tx(client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET)


def test_attack_change_input_address(client: Client):
    # input tx: d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/4h/0/0"),  # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
        prev_hash=TXHASH_d2dcda,
        amount=123_400_000,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )

    out1 = messages.TxOutputType(
        address="mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY",  # m/44h/1h/4h/0/2
        amount=100_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/4h/1/0"),  # n48agDCKBPbMLu1FYSKEpFJLradG3wgdY9
        amount=123_400_000 - 5_000 - 100_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # Test if the transaction can be signed normally
    _, serialized_tx = btc.sign_tx(
        client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
    )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "0100000001243e15b53cc553d93ec4e27e16984adc3d885ef107c613a7577fea47f5dadcd2010000006b483045022100eedaadde3a771967beee39f1daa9e9450f72fccdec63488a96d71eeae4224b4002203a22be3c1677d3451c93a49550b69e8f8fc06328823c7e0f633dde13d67ef96b01210364430c9122948e525e2f1c6d88f00f47679274f0810fd8c63754954f310995c1ffffffff02a0860100000000001976a914b3cc67f3349974d0f1b50e9bb5dfdf226f888fa088ac18555907000000001976a914f80fb232a1e54b1fa732bc120cae72eabd7fcf6888ac00000000"
    )

    attack_count = 2

    def attack_processor(msg):
        nonlocal attack_count
        if msg.tx.inputs and msg.tx.inputs[0] == inp1:
            if attack_count > 0:
                attack_count -= 1
            else:
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
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_d2dcda),
                request_input(0, TXHASH_d2dcda),
                request_output(0, TXHASH_d2dcda),
                request_output(1, TXHASH_d2dcda),
                request_input(0),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        # Now run the attack, must trigger the exception
        with pytest.raises(TrezorFailure) as exc:
            btc.sign_tx(
                client,
                "Testnet",
                [inp1],
                [out1, out2],
                prev_txes=TX_CACHE_TESTNET,
            )

        assert exc.value.code == messages.FailureType.ProcessError
        assert exc.value.message.endswith("Transaction has changed during signing")


def test_spend_coinbase(client: Client):
    # NOTE: the input transaction is not real
    # We did not have any coinbase transaction at connected with `all all` seed,
    # so it was artificially created for the test purpose

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=2_500_278_230,
        prev_hash=FAKE_TXHASH_005f6f,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="mm6FM31rM5Vc3sw5D7kztiBg3jHUzyqF1g",
        amount=2_500_278_230 - 10_000,
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
                request_meta(FAKE_TXHASH_005f6f),
                request_input(0, FAKE_TXHASH_005f6f),
                request_output(0, FAKE_TXHASH_005f6f),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "01000000013e2b623805978e1c0a4ffa4e4c10ad8f377d6036bcb3159aa00ab7f47f6f5f00000000006b483045022100a9a3e743017256fa7da39f73e7fd477edd9ba173055b32c99c99da59c23f2cde022023e4d28392f8a11967eaf8548883f9ffbb08dc7722937eb91db732fa1bef4b5b0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff01c6100795000000001976a9143d2496e67f5f57a924353da42d4725b318e7a8ea88ac00000000"
    )


def test_two_changes(client: Client):
    # input tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
    # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",  # looks like an old faucet
        amount=30_090_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out_change1 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/0"),  # mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ
        amount=900_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out_change2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/1"),  # mjXZwmEi1z1MzveZrKUAo4DBgbdq4sBYT6
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                request_output(2),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_e5040e),
                request_input(0, TXHASH_e5040e),
                request_output(0, TXHASH_e5040e),
                request_output(1, TXHASH_e5040e),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(0),
                request_output(1),
                request_output(2),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out_change1, out_change2],
            prev_txes=TX_CACHE_TESTNET,
        )


def test_change_on_main_chain_allowed(client: Client):
    # input tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
    # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",  # looks like an old faucet
        amount=30_090_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # change on main chain is allowed => treated as a change
    out_change = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=900_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_e5040e),
                request_input(0, TXHASH_e5040e),
                request_output(0, TXHASH_e5040e),
                request_output(1, TXHASH_e5040e),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out_change],
            prev_txes=TX_CACHE_TESTNET,
        )


def test_not_enough_vouts(client: Client):
    # input tx: ac4ca0e7827a1228f44449cb57b4b9a809a667ca044dc43bb124627fed4bc10a

    prev_tx = TX_CACHE_MAINNET[TXHASH_ac4ca0]

    # tx has two vouts
    assert len(prev_tx.bin_outputs) == 2

    # vout[0] and vout[1] exist
    inp0 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/55"),  # 14nw9rFTWGUncHZjSqpPSJQaptWW7iRRB8
        amount=10_000,
        prev_hash=TXHASH_ac4ca0,
        prev_index=1,
    )
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/1/7"),  # 16hgR6bjr99X6NhrsWuDR6NLpCLEacUNk
        amount=83_130,
        prev_hash=TXHASH_ac4ca0,
        prev_index=0,
    )
    # vout[2] does not exist
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/1/0"),  # 1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE
        prev_hash=TXHASH_ac4ca0,
        amount=100_000_000,
        prev_index=2,
    )

    # try to spend the sum of existing vouts
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=10_000 + 83_130 + 100_000_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(
        TrezorFailure, match="Not enough outputs in previous transaction."
    ):
        btc.sign_tx(
            client,
            "Bitcoin",
            [inp0, inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.parametrize(
    "field, value",
    (
        ("extra_data", b"hello world"),
        ("expiry", 9),
        ("timestamp", 42),
        ("version_group_id", 69),
        ("branch_id", 13),
    ),
)
def test_prevtx_forbidden_fields(client: Client, field, value):
    inp0 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),  # 1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL
        prev_hash=TXHASH_157041,
        amount=100_000_000,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=100_000_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    prev_tx = TX_CACHE_MAINNET[TXHASH_157041]
    setattr(prev_tx, field, value)
    name = field.replace("_", " ")
    with pytest.raises(TrezorFailure, match=rf"(?i){name} not enabled on this coin"):
        btc.sign_tx(
            client, "Bitcoin", [inp0], [out1], prev_txes={TXHASH_157041: prev_tx}
        )


@pytest.mark.parametrize(
    "field, value",
    (("expiry", 9), ("timestamp", 42), ("version_group_id", 69), ("branch_id", 13)),
)
def test_signtx_forbidden_fields(client: Client, field: str, value: int):
    inp0 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),  # 1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL
        prev_hash=TXHASH_157041,
        amount=100_000_000,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=1_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    kwargs = {field: value}
    name = field.replace("_", " ")
    with pytest.raises(TrezorFailure, match=rf"(?i){name} not enabled on this coin"):
        btc.sign_tx(
            client, "Bitcoin", [inp0], [out1], prev_txes=TX_CACHE_MAINNET, **kwargs
        )


@pytest.mark.parametrize(
    "script_type",
    (messages.InputScriptType.SPENDADDRESS, messages.InputScriptType.EXTERNAL),
)
def test_incorrect_input_script_type(client: Client, script_type):
    address_n = parse_path("m/44h/1h/0h/0/0")  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
    attacker_multisig_public_key = bytes.fromhex(
        "030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
    )

    multisig = messages.MultisigRedeemScriptType(
        m=1,
        nodes=[
            btc.get_public_node(client, address_n, coin_name="Testnet").node,
            messages.HDNodeType(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=bytes(32),
                public_key=attacker_multisig_public_key,
            ),
        ],
        address_n=[],
    )
    inp1 = messages.TxInputType(
        address_n=address_n,
        amount=142_920_000,
        prev_index=1,
        sequence=0xFFFFFFFF,
        script_type=script_type,  # incorrect script type
        multisig=multisig,
        prev_hash=TXHASH_e5040e,
    )
    out1 = messages.TxOutputType(
        address_n=address_n,
        amount=1_000_000 - 50_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
        multisig=multisig,
    )
    out2 = messages.TxOutputType(
        address="mtkyndbpgv1G7nwggwKDVagRpxEJrwwyh6",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(
        TrezorFailure, match="Multisig field provided but not expected."
    ):
        btc.sign_tx(client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET)


@pytest.mark.parametrize(
    "script_type",
    (
        messages.OutputScriptType.PAYTOADDRESS,
        messages.OutputScriptType.PAYTOSCRIPTHASH,
    ),
)
def test_incorrect_output_script_type(
    client: Client, script_type: messages.OutputScriptType
):
    address_n = parse_path("m/44h/1h/0h/0/0")  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
    attacker_multisig_public_key = bytes.fromhex(
        "030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
    )

    multisig = messages.MultisigRedeemScriptType(
        m=1,
        nodes=[
            btc.get_public_node(client, address_n, coin_name="Testnet").node,
            messages.HDNodeType(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=bytes(32),
                public_key=attacker_multisig_public_key,
            ),
        ],
        address_n=[],
    )
    inp1 = messages.TxInputType(
        address_n=address_n,
        amount=142_920_000,
        prev_index=1,
        sequence=0xFFFFFFFF,
        script_type=messages.InputScriptType.SPENDADDRESS,
        prev_hash=TXHASH_e5040e,
    )
    out1 = messages.TxOutputType(
        address_n=address_n,
        amount=1_000_000 - 50_000 - 10_000,
        script_type=script_type,  # incorrect script type
        multisig=multisig,
    )
    out2 = messages.TxOutputType(
        address="mtkyndbpgv1G7nwggwKDVagRpxEJrwwyh6",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(
        TrezorFailure, match="Multisig field provided but not expected."
    ):
        btc.sign_tx(client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET)


@pytest.mark.parametrize(
    "lock_time, sequence",
    ((499_999_999, 0xFFFFFFFE), (500_000_000, 0xFFFFFFFE), (1, 0xFFFFFFFF)),
)
def test_lock_time(client: Client, lock_time: int, sequence: int):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        sequence=sequence,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
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
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_0dac36),
                request_input(0, TXHASH_0dac36),
                request_output(0, TXHASH_0dac36),
                request_output(1),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1],
            lock_time=lock_time,
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.models("core", reason="Cannot test layouts on T1")
def test_lock_time_blockheight(client: Client):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        sequence=0xFFFF_FFFE,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        IF = InputFlowLockTimeBlockHeight(client, "499999999")
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1],
            lock_time=499_999_999,
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.models("core", reason="Cannot test layouts on T1")
@pytest.mark.parametrize(
    "lock_time_str", ("1985-11-05 00:53:20", "2048-08-16 22:14:00")
)
def test_lock_time_datetime(client: Client, lock_time_str: str):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        sequence=0xFFFF_FFFE,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    lock_time_naive = datetime.strptime(lock_time_str, "%Y-%m-%d %H:%M:%S")
    lock_time_utc = lock_time_naive.replace(tzinfo=timezone.utc)
    lock_time_timestamp = int(lock_time_utc.timestamp())

    with client:
        IF = InputFlowLockTimeDatetime(client, lock_time_str)
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1],
            lock_time=lock_time_timestamp,
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.models("core", reason="Cannot test layouts on T1")
def test_information(client: Client):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        sequence=0xFFFF_FFFE,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        IF = InputFlowSignTxInformation(client)
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1],
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.models("core", reason="Cannot test layouts on T1")
def test_information_mixed(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),  # mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q
        amount=31_000_000,
        prev_hash=TXHASH_e5040e,
        prev_index=0,
    )
    inp2 = messages.TxInputType(
        # tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c
        address_n=parse_path("m/86h/1h/0h/1/0"),
        amount=4_600,
        prev_hash=TXHASH_ec5194,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",
        amount=31_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        IF = InputFlowSignTxInformationMixed(client)
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )


@pytest.mark.models("core", reason="Cannot test layouts on T1")
def test_information_cancel(client: Client):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        sequence=0xFFFF_FFFE,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client, pytest.raises(Cancelled):
        IF = InputFlowSignTxInformationCancel(client)
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1],
            prev_txes=TX_CACHE_MAINNET,
        )


@pytest.mark.models(
    "core",
    skip="delizia",
    reason="Cannot test layouts on T1, not implemented in Delizia UI",
)
def test_information_replacement(client: Client):
    # Use the change output and an external output to bump the fee.
    # Originally fee was 3780, now 108060 (94280 from change and 10000 from external).

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/0/4"),
        amount=100_000,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_5e7667,
        prev_index=1,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/0/3"),
        amount=998_060,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_efaa41,
        prev_index=0,
        orig_hash=TXHASH_334cd7,
        orig_index=1,
    )

    out1 = messages.TxOutputType(
        # Actually m/49'/1'/0'/0/5.
        address="2MvUUSiQZDSqyeSdofKX9KrSCio1nANPDTe",
        amount=990_000,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    with client:
        IF = InputFlowSignTxInformationReplacement(client)
        client.set_input_flow(IF.get())

        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )
