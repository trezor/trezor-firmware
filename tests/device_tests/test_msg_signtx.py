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

from trezorlib import btc, device, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path, tx_hash

from ..common import MNEMONIC12
from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_157041 = bytes.fromhex(
    "1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6"
)
TXHASH_39a29e = bytes.fromhex(
    "39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5"
)
TXHASH_4a7b7e = bytes.fromhex(
    "4a7b7e0403ae5607e473949cfa03f09f2cd8b0f404bf99ce10b7303d86280bf7"
)
TXHASH_54aa56 = bytes.fromhex(
    "54aa5680dea781f45ebb536e53dffc526d68c0eb5c00547e323b2c32382dfba3"
)
TXHASH_58497a = bytes.fromhex(
    "58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e"
)
TXHASH_6f90f3 = bytes.fromhex(
    "6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54"
)
TXHASH_c63e24 = bytes.fromhex(
    "c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb"
)
TXHASH_c6be22 = bytes.fromhex(
    "c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)
TXHASH_d6da21 = bytes.fromhex(
    "d6da21677d7cca5f42fbc7631d062c9ae918a0254f7c6c22de8e8cb7fd5b8236"
)
TXHASH_d2dcda = bytes.fromhex(
    "d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24"
)
TXHASH_e5040e = bytes.fromhex(
    "e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd"
)
TXHASH_50f6f1 = bytes.fromhex(
    "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
)
TXHASH_2bac7a = bytes.fromhex(
    "2bac7ad1dec654579a71ea9555463f63ac7b7df9d8ba67b4682bba4e514d0f0c"
)


class TestMsgSigntx:
    def test_one_one_fee(self, client):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390000 - 10000,
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
                    request_meta(TXHASH_d5f65e),
                    request_input(0, TXHASH_d5f65e),
                    request_input(1, TXHASH_d5f65e),
                    request_output(0, TXHASH_d5f65e),
                    request_input(0),
                    request_output(0),
                    request_output(0),
                    request_finished(),
                ]
            )

            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
            )

        assert (
            tx_hash(serialized_tx).hex()
            == "f6b22f324894c708e32d340a60af670c8accb3b62d05906d31e60ae49696c0c3"
        )

    def test_testnet_one_two_fee(self, client):
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",
            amount=30090000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/1/0"),
            amount=900000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
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

        assert (
            serialized_tx.hex()
            == "0100000001cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100eba3bbcbb82ab1ebac88a394e8fb53b0263dadbb3e8072f0a21ee62818c911060220686a9b7f306d028b54a228b5c47cc6c27b1d01a3b0770440bcc64d55d8bace2c0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff021023cb01000000001976a91485eb47fe98f349065d6f044e27a4ac541af79ee288aca0bb0d00000000001976a9143d3cca567e00a04819742b21a696a67da796498b88ac00000000"
        )

    def test_testnet_fee_high_warning(self, client):
        # tx: 6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54
        # input 1: 10.00000000 BTC
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=1000000000,
            prev_hash=TXHASH_6f90f3,
            prev_index=1,
        )

        out1 = messages.TxOutputType(
            address="mfiGQVPcRcaEvQPYDErR34DcCovtxYvUUV",
            amount=1000000000 - 500000000 - 8000000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/1/0"),
            amount=500000000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    messages.ButtonRequest(code=B.FeeOverThreshold),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_6f90f3),
                    request_input(0, TXHASH_6f90f3),
                    request_input(1, TXHASH_6f90f3),
                    request_output(0, TXHASH_6f90f3),
                    request_output(1, TXHASH_6f90f3),
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

        assert (
            tx_hash(serialized_tx).hex()
            == "54fd5e9b65b8acc10144c1e78ea9720df7606d7d4a543e4c547ecd45b2ae226b"
        )

    def test_one_two_fee(self, client):
        # tx: c275c333fd1b36bef4af316226c66a8b3693fbfcc081a5e16a2ae5fcb09e92bf

        inp1 = messages.TxInputType(
            address_n=parse_path(
                "m/44'/0'/0'/0/5"
            ),  # 1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ
            amount=50000,
            prev_hash=TXHASH_50f6f1,
            prev_index=1,
        )

        out1 = messages.TxOutputType(
            address_n=parse_path(
                "m/44'/0'/0'/1/3"
            ),  # 1EcL6AyfQTyWKGvXwNSfsWoYnD3whzVFdu
            amount=30000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address="1Up15Msx4sbvUCGm8Xgo2Zp5FQim3wE59",
            amount=10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    messages.ButtonRequest(code=B.ConfirmOutput),
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

        assert (
            serialized_tx.hex()
            == "01000000016d20f69067ad1ffd50ee7c0f377dde2c932ccb03e84b5659732da99c20f1f650010000006a47304402203429bd3ce7b38c5c1e8a15340edd79ced41a2939aae62e259d2e3d18e0c5ee7602201b83b10ebc4d6dcee3f9eb42ba8f1ef8a059a05397e0c1b9223d1565a3e6ec01012102a7a079c1ef9916b289c2ff21a992c808d0de3dfcf8a9f163205c5c9e21f55d5cffffffff0230750000000000001976a914954820f1de627a703596ac0396f986d958e3de4c88ac10270000000000001976a91405427736705cfbfaff76b1cff48283707fb1037088ac00000000"
        )

    def test_one_three_fee(self, client):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44'/0'/0'/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390000 - 80000 - 12000 - 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address="13uaUYn6XAooo88QvAqAVsiVvr2mAXutqP",
            amount=12000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out3 = messages.TxOutputType(
            address_n=parse_path("44'/0'/0'/1/0"),
            amount=80000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    request_output(2),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_d5f65e),
                    request_input(0, TXHASH_d5f65e),
                    request_input(1, TXHASH_d5f65e),
                    request_output(0, TXHASH_d5f65e),
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
                "Bitcoin",
                [inp1],
                [out1, out2, out3],
                prev_txes=TX_CACHE_MAINNET,
            )

        assert (
            tx_hash(serialized_tx).hex()
            == "fedbba83b115725a713c2b1a13db09fd33de582132d520a3f6ff72503ca5da61"
        )

    def test_two_two(self, client):
        # tx: c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c
        # input 1: 0.0010 BTC
        # tx: 58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e
        # input 1: 0.0011 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=100000,
            prev_hash=TXHASH_c6be22,
            prev_index=1,
        )

        inp2 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/1"),
            amount=110000,
            prev_hash=TXHASH_58497a,
            prev_index=1,
        )

        out1 = messages.TxOutputType(
            address="15Jvu3nZNP7u2ipw2533Q9VVgEu2Lu9F2B",
            amount=210000 - 100000 - 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44h/0h/0h/1/0"),
            amount=100000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_c6be22),
                    request_input(0, TXHASH_c6be22),
                    request_output(0, TXHASH_c6be22),
                    request_output(1, TXHASH_c6be22),
                    request_input(1),
                    request_meta(TXHASH_58497a),
                    request_input(0, TXHASH_58497a),
                    request_output(0, TXHASH_58497a),
                    request_output(1, TXHASH_58497a),
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

        # Accepted by network: tx c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        # The transaction was produced before Trezor implemented BIP-66, so the signature
        # is now different and txhash doesn't match what is on the blockchain.
        assert (
            tx_hash(serialized_tx).hex()
            == "6f9775545830731a316a4c2a39515b1890e9c8ab0f9e21e7c6a6ca2c1499116d"
        )

    @pytest.mark.skip_ui
    @pytest.mark.slow
    def test_lots_of_inputs(self, client):
        # Tests if device implements serialization of len(inputs) correctly
        # tx 4a7b7e0403ae5607e473949cfa03f09f2cd8b0f404bf99ce10b7303d86280bf7 : 100 UTXO for spending for unit tests
        inputs = []
        for i in range(100):
            inputs.append(
                messages.TxInputType(
                    address_n=parse_path(f"44h/0h/0h/0/{i}"),
                    amount=26000,
                    prev_hash=TXHASH_4a7b7e,
                    prev_index=i,
                )
            )
        out = messages.TxOutputType(
            address="19dvDdyxxptP9dGvozYe8BP6tgFV9L4jg5",
            amount=100 * 26000 - 15 * 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", inputs, [out], prev_txes=TX_CACHE_MAINNET
        )
        assert (
            tx_hash(serialized_tx).hex()
            == "f90cdc2224366312be28166e2afe198ece7a60e86e25f5a50f5b14d811713da8"
        )

    @pytest.mark.skip_ui
    @pytest.mark.slow
    def test_lots_of_outputs(self, client):
        # Tests if device implements serialization of len(outputs) correctly

        # tx: c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        # index 1: 0.0010 BTC
        # tx: 39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5
        # index 1: 0.0254 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/1h/0/0"),
            amount=100000,
            prev_hash=TXHASH_c63e24,
            prev_index=1,
        )

        inp2 = messages.TxInputType(
            address_n=parse_path("44h/0h/1h/0/1"),
            amount=2540000,
            prev_hash=TXHASH_39a29e,
            prev_index=1,
        )

        outputs = []
        cnt = 255
        for _ in range(cnt):
            out = messages.TxOutputType(
                address="1NwN6UduuVkJi6sw3gSiKZaCY5rHgVXC2h",
                amount=(100000 + 2540000 - 39000) // cnt,
                script_type=messages.OutputScriptType.PAYTOADDRESS,
            )
            outputs.append(out)

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1, inp2], outputs, prev_txes=TX_CACHE_MAINNET
        )

        assert (
            tx_hash(serialized_tx).hex()
            == "aa0cfe57938b71db47a3992b25d4bee39f258a5de513c907727b982478648a7d"
        )

    @pytest.mark.slow
    def test_lots_of_change(self, client):
        # Tests if device implements prompting for multiple change addresses correctly

        # tx: c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        # index 1: 0.0010 BTC
        # tx: 39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5
        # index 1: 0.0254 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/1h/0/0"),
            amount=100000,
            prev_hash=TXHASH_c63e24,
            prev_index=1,
        )

        inp2 = messages.TxInputType(
            address_n=parse_path("44h/0h/1h/0/1"),
            amount=2540000,
            prev_hash=TXHASH_39a29e,
            prev_index=1,
        )

        outputs = [
            messages.TxOutputType(
                address="1NwN6UduuVkJi6sw3gSiKZaCY5rHgVXC2h",
                amount=500000,
                script_type=messages.OutputScriptType.PAYTOADDRESS,
            )
        ]

        cnt = 20
        for i in range(cnt):
            out = messages.TxOutputType(
                address_n=parse_path(f"44h/0h/1h/1/{i}"),
                amount=(100000 + 2540000 - 500000 - 39000) // cnt,
                script_type=messages.OutputScriptType.PAYTOADDRESS,
            )
            outputs.append(out)

        request_change_outputs = [request_output(i + 1) for i in range(cnt)]

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                ]
                + request_change_outputs
                + [
                    messages.ButtonRequest(code=B.SignTx),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_c63e24),
                    request_input(0, TXHASH_c63e24),
                    request_input(1, TXHASH_c63e24),
                    request_output(0, TXHASH_c63e24),
                    request_output(1, TXHASH_c63e24),
                    request_input(1),
                    request_meta(TXHASH_39a29e),
                    request_input(0, TXHASH_39a29e),
                    request_output(0, TXHASH_39a29e),
                    request_output(1, TXHASH_39a29e),
                    request_input(0),
                    request_input(1),
                    request_output(0),
                ]
                + request_change_outputs
                + [request_input(0), request_input(1), request_output(0)]
                + request_change_outputs
                + [request_output(0)]
                + request_change_outputs
                + [request_finished()]
            )

            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1, inp2], outputs, prev_txes=TX_CACHE_MAINNET
            )

        assert (
            tx_hash(serialized_tx).hex()
            == "fae68e4a3a4b0540eb200e2218a6d8465eac469788ccb236e0d5822d105ddde9"
        )

    def test_fee_high_warning(self, client):
        # tx: 1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6
        # input 0: 1.0 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=100000000,
            prev_hash=TXHASH_157041,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=100000000 - 510000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    messages.ButtonRequest(code=B.FeeOverThreshold),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_157041),
                    request_input(0, TXHASH_157041),
                    request_output(0, TXHASH_157041),
                    request_output(1, TXHASH_157041),
                    request_input(0),
                    request_output(0),
                    request_output(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
            )

        assert (
            tx_hash(serialized_tx).hex()
            == "c36928aca6452d50cb63e2592200bbcc3722ce6b631b1dfd185ccdf9a954af28"
        )

    @pytest.mark.skip_t1
    def test_fee_high_hardfail(self, client):
        # tx: 1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6
        # input 0: 1.0 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=100000000,
            prev_hash=TXHASH_157041,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=100000000 - 5100000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with pytest.raises(TrezorFailure, match="fee is unexpectedly large"):
            btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)

        # set SafetyCheckLevel to Prompt and try again
        device.apply_settings(client, safety_checks=messages.SafetyCheckLevel.Prompt)
        with client:
            finished = False

            def input_flow():
                nonlocal finished
                for expected in (B.ConfirmOutput, B.FeeOverThreshold, B.SignTx):
                    br = yield
                    assert br == expected
                    client.debug.press_yes()
                finished = True

            client.set_input_flow(input_flow)

            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
            )
            assert finished

        assert (
            tx_hash(serialized_tx).hex()
            == "0fadc325662e84fd1a5efcb20c5369cf9134a24b6d29bce99f61e69680397a79"
        )

    def test_not_enough_funds(self, client):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=400000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    messages.Failure(code=messages.FailureType.NotEnoughFunds),
                ]
            )
            with pytest.raises(TrezorFailure, match="NotEnoughFunds"):
                btc.sign_tx(
                    client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
                )

    def test_p2sh(self, client):
        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=400000,
            prev_hash=TXHASH_54aa56,
            prev_index=1,
        )

        out1 = messages.TxOutputType(
            address="3DKGE1pvPpBAgZj94MbCinwmksewUNNYVR",  # p2sh
            amount=400000 - 10000,
            script_type=messages.OutputScriptType.PAYTOSCRIPTHASH,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_54aa56),
                    request_input(0, TXHASH_54aa56),
                    request_output(0, TXHASH_54aa56),
                    request_output(1, TXHASH_54aa56),
                    request_input(0),
                    request_output(0),
                    request_output(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
            )

        assert (
            tx_hash(serialized_tx).hex()
            == "5042aed319b9f018d693dbf8f3db926ee4ab4dae670a2911625b440a1366f79d"
        )

    def test_testnet_big_amount(self, client):
        # This test is testing transaction with amount bigger than fits to uint32

        # tx: 2bac7ad1dec654579a71ea9555463f63ac7b7df9d8ba67b4682bba4e514d0f0c:1
        # input 1: 411102528330 Satoshi

        inp1 = messages.TxInputType(
            address_n=parse_path("m/44'/1'/0'/0/0"),
            amount=411102528330,
            prev_hash=TXHASH_2bac7a,
            prev_index=1,
        )
        out1 = messages.TxOutputType(
            address="mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b",  # seed allallall, bip32: m/44'/1'/0'/0/1
            amount=411102528330,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
        )
        assert (
            serialized_tx.hex()
            == "01000000010c0f4d514eba2b68b467bad8f97d7bac633f465595ea719a5754c6ded17aac2b010000006b4830450221008e3b926f04d8830bd5b67698af25c9e00c9db1b1ef3e5d69af794446753da94a02202d4a7509f26bba29ff643a7ac0d43fb128c1a632cc502b8f44eada8930fb9c9b0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff014ac39eb75f0000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac00000000"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_attack_change_outputs(self, client):
        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=100000,
            prev_hash=TXHASH_c6be22,
            prev_index=1,
        )

        inp2 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/1"),
            amount=110000,
            prev_hash=TXHASH_58497a,
            prev_index=1,
        )

        out1 = messages.TxOutputType(
            address="15Jvu3nZNP7u2ipw2533Q9VVgEu2Lu9F2B",
            amount=210000 - 100000 - 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44h/0h/0h/1/0"),
            amount=100000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        # Test if the transaction can be signed normally
        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1, inp2], [out1, out2], prev_txes=TX_CACHE_MAINNET
        )

        assert (
            tx_hash(serialized_tx).hex()
            == "4601b738e1b0f8a7ff9ca5adf0c896fa39dfe8b8ead7ad0d716c98167e8a5d11"
        )

        run_attack = False

        def attack_processor(msg):
            nonlocal run_attack
            if msg.tx.outputs and msg.tx.outputs[0] == out2:
                if not run_attack:
                    run_attack = True
                else:
                    # Sign output with another amount
                    msg.tx.outputs[0].amount = 9999999

            return msg

        # Set up attack processors
        client.set_filter(messages.TxAck, attack_processor)

        with pytest.raises(
            TrezorFailure, match="Transaction has changed during signing"
        ):
            btc.sign_tx(
                client,
                "Bitcoin",
                [inp1, inp2],
                [out1, out2],
                prev_txes=TX_CACHE_MAINNET,
            )

    # Ensure that if the change output is modified after the user confirms the
    # transaction, then signing fails.
    def test_attack_modify_change_address(self, client):
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",
            amount=30090000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/1/0"),
            amount=900000,
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
                    msg.tx.outputs[0].address = "mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY"

            return msg

        # Set up attack processors
        client.set_filter(messages.TxAck, attack_processor)

        with pytest.raises(
            TrezorFailure, match="Transaction has changed during signing"
        ):
            btc.sign_tx(
                client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
            )

    def test_attack_change_input_address(self, client):
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/4'/0/0"),
            # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
            prev_hash=TXHASH_d2dcda,
            amount=123400000,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDADDRESS,
        )

        out1 = messages.TxOutputType(
            address="mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY",
            amount=100000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out2 = messages.TxOutputType(
            address_n=parse_path("44'/1'/4'/1/0"),
            amount=123400000 - 5000 - 100000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        # Test if the transaction can be signed normally
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
        )

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

        client.set_filter(messages.TxAck, attack_processor)
        # Now run the attack, must trigger the exception
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
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
                    client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET,
                )

            assert exc.value.code == messages.FailureType.ProcessError
            if client.features.model == "1":
                assert exc.value.message.endswith("Failed to compile input")
            else:
                assert exc.value.message.endswith(
                    "Transaction has changed during signing"
                )

    def test_spend_coinbase(self, client):
        inp1 = messages.TxInputType(
            address_n=parse_path("44h/1h/0h/0/0"),
            amount=2500278230,
            prev_hash=TXHASH_d6da21,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="mm6FM31rM5Vc3sw5D7kztiBg3jHUzyqF1g",
            amount=2500278230 - 10000,
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
                    request_meta(TXHASH_d6da21),
                    request_input(0, TXHASH_d6da21),
                    request_output(0, TXHASH_d6da21),
                    request_input(0),
                    request_output(0),
                    request_output(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
            )

        # Accepted by network: tx
        assert (
            tx_hash(serialized_tx).hex()
            == "cf5a8ad5a4f0211953e0d40d9145d6651f0d90203e52913e780065bd00840da3"
        )

    def test_two_changes(self, client):
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",
            amount=30090000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out_change1 = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/1/0"),
            amount=900000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        out_change2 = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/1/1"),
            amount=10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
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

    def test_change_on_main_chain_allowed(self, client):
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = messages.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = messages.TxOutputType(
            address="msj42CCGruhRsFrGATiUuh25dtxYtnpbTx",
            amount=30090000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        # change on main chain is allowed => treated as a change
        out_change = messages.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=900000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
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

    @pytest.mark.skip_ui
    def test_not_enough_vouts(self, client):
        prev_tx = TX_CACHE_MAINNET[TXHASH_157041]

        # tx has two vouts
        assert len(prev_tx.bin_outputs) == 2

        # vout[0] and vout[1] exist
        inp0 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            prev_hash=TXHASH_157041,
            amount=100000000,
            prev_index=0,
        )
        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/1"),
            prev_hash=TXHASH_157041,
            amount=120160000,
            prev_index=1,
        )
        # vout[2] does not exist
        inp2 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/1/0"),
            prev_hash=TXHASH_157041,
            amount=100000000,
            prev_index=2,
        )

        # try to spend the sum of existing vouts
        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=100000000 + 120160000 + 100000000 - 10000,
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
    @pytest.mark.skip_ui
    def test_prevtx_forbidden_fields(self, client, field, value):
        inp0 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            prev_hash=TXHASH_157041,
            amount=100000000,
            prev_index=0,
        )
        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=100000000 - 1000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        prev_tx = TX_CACHE_MAINNET[TXHASH_157041]
        setattr(prev_tx, field, value)
        name = field.replace("_", " ")
        with pytest.raises(
            TrezorFailure, match=r"(?i){} not enabled on this coin".format(name)
        ):
            btc.sign_tx(
                client, "Bitcoin", [inp0], [out1], prev_txes={TXHASH_157041: prev_tx}
            )

    @pytest.mark.parametrize(
        "field, value",
        (("expiry", 9), ("timestamp", 42), ("version_group_id", 69), ("branch_id", 13)),
    )
    @pytest.mark.skip_ui
    def test_signtx_forbidden_fields(self, client, field, value):
        inp0 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            prev_hash=TXHASH_157041,
            amount=100000000,
            prev_index=0,
        )
        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=1000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        details = messages.SignTx()
        setattr(details, field, value)
        name = field.replace("_", " ")
        with pytest.raises(
            TrezorFailure, match=r"(?i){} not enabled on this coin".format(name)
        ):
            btc.sign_tx(
                client, "Bitcoin", [inp0], [out1], details, prev_txes=TX_CACHE_MAINNET
            )

    @pytest.mark.parametrize(
        "script_type",
        (messages.InputScriptType.SPENDADDRESS, messages.InputScriptType.EXTERNAL),
    )
    @pytest.mark.skip_ui
    def test_incorrect_input_script_type(self, client, script_type):
        address_n = parse_path("44'/1'/0'/0/0")
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
            amount=142920000,
            prev_index=1,
            sequence=0xFFFFFFFF,
            script_type=script_type,  # incorrect script type
            multisig=multisig,
            prev_hash=TXHASH_e5040e,
        )
        out1 = messages.TxOutputType(
            address_n=address_n,
            amount=1000000 - 50000 - 10000,
            script_type=messages.OutputScriptType.PAYTOMULTISIG,
            multisig=multisig,
        )
        out2 = messages.TxOutputType(
            address="mtkyndbpgv1G7nwggwKDVagRpxEJrwwyh6",
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with pytest.raises(
            TrezorFailure, match="Multisig field provided but not expected."
        ):
            btc.sign_tx(
                client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
            )

    @pytest.mark.parametrize(
        "script_type",
        (
            messages.OutputScriptType.PAYTOADDRESS,
            messages.OutputScriptType.PAYTOSCRIPTHASH,
        ),
    )
    @pytest.mark.skip_ui
    def test_incorrect_output_script_type(self, client, script_type):
        address_n = parse_path("44'/1'/0'/0/0")
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
            amount=142920000,
            prev_index=1,
            sequence=0xFFFFFFFF,
            script_type=messages.InputScriptType.SPENDADDRESS,
            prev_hash=TXHASH_e5040e,
        )
        out1 = messages.TxOutputType(
            address_n=address_n,
            amount=1000000 - 50000 - 10000,
            script_type=script_type,  # incorrect script type
            multisig=multisig,
        )
        out2 = messages.TxOutputType(
            address="mtkyndbpgv1G7nwggwKDVagRpxEJrwwyh6",
            amount=50000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with pytest.raises(
            TrezorFailure, match="Multisig field provided but not expected."
        ):
            btc.sign_tx(
                client, "Testnet", [inp1], [out1, out2], prev_txes=TX_CACHE_TESTNET
            )

    @pytest.mark.parametrize(
        "lock_time, sequence",
        ((499999999, 0xFFFFFFFE), (500000000, 0xFFFFFFFE), (1, 0xFFFFFFFF)),
    )
    def test_lock_time(self, client, lock_time, sequence):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = messages.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
            sequence=sequence,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390000 - 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    messages.ButtonRequest(code=B.SignTx),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_d5f65e),
                    request_input(0, TXHASH_d5f65e),
                    request_input(1, TXHASH_d5f65e),
                    request_output(0, TXHASH_d5f65e),
                    request_input(0),
                    request_output(0),
                    request_output(0),
                    request_finished(),
                ]
            )

            details = messages.SignTx(lock_time=lock_time)
            btc.sign_tx(
                client,
                "Bitcoin",
                [inp1],
                [out1],
                details=details,
                prev_txes=TX_CACHE_MAINNET,
            )
