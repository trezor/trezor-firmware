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

from trezorlib import btc, messages as proto
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, btc_hash, parse_path

from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = proto.ButtonRequestType
TX_API = TxCache("Bgold")

TXHASH_25526b = bytes.fromhex(
    "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
)
TXHASH_db77c2 = bytes.fromhex(
    "db77c2461b840e6edbe7f9280043184a98e020d9795c1b65cb7cef2551a8fb18"
)
TXHASH_f55c5b = bytes.fromhex(
    "f55c5bc925eb2a0bf9de0ac142b24bed81ec46dd2151d5f69728070eaea1aded"
)


# All data taken from T1
@pytest.mark.altcoin
class TestMsgSigntxBitcoinGold:
    def test_send_bitcoin_gold_change(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/0/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/156'/0'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1252382934 - 1896050 - 1000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "39a0716c361610724c7c40916baa20808cbdd7538b6c38689ce80cb73e7f51d1"
        )

    def test_send_bitcoin_gold_nochange(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/1/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/0/1"),
            # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
            amount=38448607,
            prev_hash=TXHASH_db77c2,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1252382934 + 38448607 - 1000,
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
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(1),
                    request_meta(TXHASH_db77c2),
                    request_input(0, TXHASH_db77c2),
                    request_input(1, TXHASH_db77c2),
                    request_output(0, TXHASH_db77c2),
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "ac9d452b900eb747d3137e1f3044bb0f46efaeb6e0fc8c27b02d1d08d238a904"
        )

    def test_attack_change_input(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/11'/0/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/156'/11'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1252382934 - 1896050 - 1000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        attack_count = 2

        def attack_processor(msg):
            nonlocal attack_count

            if msg.tx.inputs and msg.tx.inputs[0] == inp1:
                if attack_count > 0:
                    attack_count -= 1
                else:
                    msg.tx.inputs[0].address_n[2] = H_(1)

            return msg

        with client:
            client.set_filter(proto.TxAck, attack_processor)
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    proto.Failure(code=proto.FailureType.ProcessError),
                ]
            )
            with pytest.raises(TrezorFailure):
                btc.sign_tx(client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API)

    @pytest.mark.multisig
    def test_send_btg_multisig_change(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path(f"48'/156'/{i}'/0'"), coin_name="Bgold"
            ).node
            for i in range(1, 4)
        ]

        EMPTY_SIGS = [b"", b"", b""]

        def getmultisig(chain, nr, signatures):
            return proto.MultisigRedeemScriptType(
                nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
            )

        inp1 = proto.TxInputType(
            address_n=parse_path("48'/156'/3'/0'/0/0"),
            multisig=getmultisig(0, 0, EMPTY_SIGS),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=24000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("48'/156'/3'/0'/1/0"),
            multisig=getmultisig(1, 0, EMPTY_SIGS),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=1252382934 - 24000 - 1000,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    request_finished(),
                ]
            )
            signatures, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            signatures[0].hex()
            == "30440220263c427e6e889c161206edee39b9b969350c154ddd8eb76d2ab8ca8e0fc083b702200fb1d0ef430fa2d0293dcbb0b237775d4f9748222a6ed9fc3ff747837b99020a"
        )

        inp1 = proto.TxInputType(
            address_n=parse_path("48'/156'/1'/0'/0/0"),
            multisig=getmultisig(0, 0, [b"", b"", signatures[0]]),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out2.address_n[2] = H_(1)

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    request_finished(),
                ]
            )
            signatures, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            signatures[0].hex()
            == "3045022100c9094b060b4b095e78403493912b0e06ca12ffbdc0f2fbeec20b02d7eaa73f8702206813e33e04a2b9c4493ecfa2024f2e9d69b5a2ab5c10433d9ab762add5bdde27"
        )
        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "2677130ec0c5eea2249787fe17b85770cfb35dfce550830a7fb6c6acd9375114"
        )

    def test_send_p2sh(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=12300000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GZFLExxrvWFuFT1xRzhfwQWSE2bPDedBfn",
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            amount=1252382934 - 11000 - 12300000,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    request_input(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "d5732fc8a594ae3b7ba695d7b276b2186f8572b0eb157120e0ba35d3511c6060"
        )

    def test_send_p2sh_witness_change(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=12300000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            script_type=proto.OutputScriptType.PAYTOP2SHWITNESS,
            amount=1252382934 - 11000 - 12300000,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    request_input(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "eed4ef86a408602e35ae416591f349847db38cdaddef1429a9bb0e39520d100d"
        )

    @pytest.mark.multisig
    def test_send_multisig_1(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path(f"49'/156'/{i}'"), coin_name="Bgold"
            ).node
            for i in range(1, 4)
        ]
        multisig = proto.MultisigRedeemScriptType(
            nodes=nodes, address_n=[1, 0], signatures=[b"", b"", b""], m=2
        )

        inp1 = proto.TxInputType(
            address_n=parse_path("49'/156'/1'/1/0"),
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            amount=1252382934,
        )

        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1252382934 - 1000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_input(0),
                    request_finished(),
                ]
            )
            signatures, _ = btc.sign_tx(
                client, "Bgold", [inp1], [out1], prev_txes=TX_API
            )
            # store signature
            inp1.multisig.signatures[0] = signatures[0]
            # sign with third key
            inp1.address_n[2] = H_(3)
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(0),
                    request_output(0),
                    request_input(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1], [out1], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "efa5b21916ac7ea5316c38b2d7d5520d80cbe563c58304f956ea6ddb241001d1"
        )

    def test_send_mixed_inputs(self, client):
        # First is non-segwit, second is segwit.

        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/11'/0/0"),
            amount=38448607,
            prev_hash=TXHASH_db77c2,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=38448607 + 1252382934 - 1000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "2c64109fba890657e37f0782efda29bbc277dfd521658f185d302ddffcacffd2"
        )

    @pytest.mark.skip_t1
    def test_send_btg_external_presigned(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/1/0"),
            amount=1252382934,
            prev_hash=TXHASH_25526b,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            # address_n=parse_path("49'/156'/0'/0/0"),
            # AXibjT5r96ZaVA8Lu4BQZocdTx7p5Ud8ZP
            amount=58456,
            prev_hash=TXHASH_f55c5b,
            prev_index=0,
            script_type=proto.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex(
                "a914aee37ad448e17438cabfee1756f2a08e33ed3ce887"
            ),
            script_sig=bytes.fromhex("1600147c5edda9b293db2c8894b9d81efd77764910c445"),
            witness=bytes.fromhex(
                "024730440220091eece828409b3a9aa92dd2f9b032f9fb3a12b21b323a3fdea3cb18d08249af022065412107afcf76b0d28b90188c802f8f17b41790ed81c868d0ee23f1dd2ec53441210386789a34fe1a49bfc3e174adc6706c6222b0d80de76b884a0e3d32f8e9c4dc3e"
            ),
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1252382934 + 58456 - 1000,
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
                    request_meta(TXHASH_25526b),
                    request_input(0, TXHASH_25526b),
                    request_output(0, TXHASH_25526b),
                    request_output(1, TXHASH_25526b),
                    request_input(1),
                    request_meta(TXHASH_f55c5b),
                    request_input(0, TXHASH_f55c5b),
                    request_output(0, TXHASH_f55c5b),
                    request_output(1, TXHASH_f55c5b),
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    request_input(1),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
            )

        assert (
            btc_hash(serialized_tx)[::-1].hex()
            == "95ebe5cdfb8dc3c112eb0107fc3bd7701689ac5ec4a74a3d12e203333d0832d3"
        )
