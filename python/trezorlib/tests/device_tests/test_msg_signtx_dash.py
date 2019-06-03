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
from trezorlib.exceptions import Cancelled
from trezorlib.tools import parse_path

from ..support.tx_cache import tx_cache
from .common import TrezorTest

TX_API = tx_cache("Dash")


class TestMsgSigntxDash(TrezorTest):
    def test_send_dash(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/5'/0'/0/0"),
            # dash:XdTw4G5AWW4cogGd7ayybyBNDbuB45UpgH
            amount=1000000000,
            prev_hash=bytes.fromhex(
                "5579eaa64b2a0233e7d8d037f5a5afc957cedf48f1c4067e9e33ca6df22ab04f"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="XpTc36DPAeWmaueNBA9JqCg2GC8XDLKSYe",
            amount=999999000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash", [inp1], [out1], prev_txes=TX_API
            )

        assert (
            serialized_tx.hex()
            == "01000000014fb02af26dca339e7e06c4f148dfce57c9afa5f537d0d8e733022a4ba6ea7955010000006a4730440220387be4d1e4b5e355614091416373e99e1a3532b8cc9a8629368060aff2681bdb02200a0c4a5e9eb2ce6adb6c2e01ec8f954463dcc04f531ed8a89a2b40019d5aeb0b012102936f80cac2ba719ddb238646eb6b78a170a55a52a9b9f08c43523a4a6bd5c896ffffffff0118c69a3b000000001976a9149710d6545407e78c326aa8c8ae386ec7f883b0af88ac00000000"
        )

    def test_send_dash_dip2_input(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/5'/0'/0/0"),
            # dash:XdTw4G5AWW4cogGd7ayybyBNDbuB45UpgH
            amount=4095000260,
            prev_hash=bytes.fromhex(
                "15575a1c874bd60a819884e116c42e6791c8283ce1fc3b79f0d18531a61bbb8a"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/5'/0'/1/0"),
            amount=4000000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="XrEFMNkxeipYHgEQKiJuqch8XzwrtfH5fm",
            amount=95000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=39,
                            extra_data_offset=0,
                            tx_hash=inp1.prev_hash,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash", [inp1], [out1, out2], prev_txes=TX_API
            )

        assert (
            serialized_tx.hex()
            == "01000000018abb1ba63185d1f0793bfce13c28c891672ec416e18498810ad64b871c5a5715010000006b483045022100f0442b6d9c7533cd6f74afa993b280ed9475276d69df4dac631bc3b5591ba71b022051daf125372c1c477681bbd804a6445d8ff6840901854fb0b485b1c6c7866c44012102936f80cac2ba719ddb238646eb6b78a170a55a52a9b9f08c43523a4a6bd5c896ffffffff0200286bee000000001976a914fd61dd017dad1f505c0511142cc9ac51ef3a5beb88acc095a905000000001976a914aa7a6a1f43dfc34d17e562ce1845b804b73fc31e88ac00000000"
        )

    def test_send_dash_dip2_proregtx(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0/0"),
            amount=100000000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=709999000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "d1010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c5a2d505da4f03b2776f588e4fee0118248dc044126d93a264c52fb494ed0eaa6ae71c2843fccf152e42b436193e16218256080339155421de6ecb19bede83b125ac0d50c5a2d505da4f03b2776f588e4fee0118248dc04400001976a914a579388225827d9f2fe9014add644487808c695d88acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a50000"
            )
        txdata = proto.SignTx()
        txdata.version = (1 << 16) | 3
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=202,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=202,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=202,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1, out2], details=txdata, prev_txes=TX_API, extra_payload=extra_payload
            )
        assert (
            serialized_tx.hex()
            == "03000100018dc5f38fcb801a6fad31de622a226e5b1886b1fecac41ada087d5c23be016e69010000006b483045022100f3ba5d64e79d68228de39f5ffd14d26324d5346f4808420fd90698267b598449022022bebdab8def40d07d4cce5df7d45420e656436bb3f48b95bbfc005ea40aabf10121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0200e87648170000001976a9149e87e0cb3156d46468dde382b57964a9810991c088ac98b9512a000000001976a914a579388225827d9f2fe9014add644487808c695d88ac00000000d1010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c5a2d505da4f03b2776f588e4fee0118248dc044126d93a264c52fb494ed0eaa6ae71c2843fccf152e42b436193e16218256080339155421de6ecb19bede83b125ac0d50c5a2d505da4f03b2776f588e4fee0118248dc04400001976a914a579388225827d9f2fe9014add644487808c695d88acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a50000"
        )

    def test_send_dash_dip2_proregtx_external(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=100709999750,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "fd12010100000000009b9054ff7839b940277b8eb8211570b2f16850ef729ee635e24d722fbc4a46230100000000000000000000000000ffffc6c74af14e1fc5a2d505da4f03b2776f588e4fee0118248dc044972f4481e23ea3b34a974349c44d8b96974ffb1e83cecb879564dcaa8b3ef58d84866dd672ad3d2db73904a9fa5c3b06c5a2d505da4f03b2776f588e4fee0118248dc0440b091976a914a579388225827d9f2fe9014add644487808c695d88acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a500412008ed82d28a503a49dc925b99b386876921958cc528134280ea4d5de6935b6b342cba08fda8e25701ae5efa8baa3a1fae12c2f2a1e044a4f42161b429eb994f5d"
            )
        collateral_id = bytes.fromhex("23464abc2f724de235e69e72ef5068f1b2701521b88e7b2740b93978ff54909b")
        collateral_out = 1
        txdata = proto.SignTx()
        txdata.version = (1 << 16) | 3
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=269,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=collateral_out,
                            tx_hash=collateral_id,
                        ),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=269,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=269,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1], details=txdata,
                prev_txes=TX_API, extra_payload=extra_payload,
                external_txes=[collateral_id]
            )
        assert (
            serialized_tx.hex()
            == "03000100018dc5f38fcb801a6fad31de622a226e5b1886b1fecac41ada087d5c23be016e69010000006b483045022100bcdd402ec925b970aac0cd903f8165d670567b0781dfbf256a46b55f95d58b2d022060924bf9723ffe4048525d0f4a7a306164cc6c5cd120b6db8b71c8ec90742a310121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0186a4c872170000001976a914a579388225827d9f2fe9014add644487808c695d88ac00000000fd12010100000000009b9054ff7839b940277b8eb8211570b2f16850ef729ee635e24d722fbc4a46230100000000000000000000000000ffffc6c74af14e1fc5a2d505da4f03b2776f588e4fee0118248dc044972f4481e23ea3b34a974349c44d8b96974ffb1e83cecb879564dcaa8b3ef58d84866dd672ad3d2db73904a9fa5c3b06c5a2d505da4f03b2776f588e4fee0118248dc0440b091976a914a579388225827d9f2fe9014add644487808c695d88acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a500412008ed82d28a503a49dc925b99b386876921958cc528134280ea4d5de6935b6b342cba08fda8e25701ae5efa8baa3a1fae12c2f2a1e044a4f42161b429eb994f5d"
        )

    def test_send_dash_dip2_proupservtx(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=100709999750,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "b5010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a13900000000000000000000ffffc6c74af14e1f00c3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a50006eb32f14e5da95f1fbd56f49d0f1cf44e4aafc7f595c258937a37ab3ca5b9faa7857d7e382eb64731b733fdba899c5418f4b11f05e3b129c53db2bb3f4d94bc100cdce626e712055eb79cb2448a084e52f25c62c28259bd3323302faa29b6f8"
            )
        proregtx_id = bytes.fromhex(
            "39a1339d9bf26de701345beecc5de75a690bc9533741a3dbe90f2fd88b8ed461"
        )
        txdata = proto.SignTx()
        txdata.version = (2 << 16) | 3
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=174,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=proregtx_id),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=174,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=174,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1], details=txdata,
                prev_txes=TX_API, extra_payload=extra_payload,
                external_txes=[proregtx_id]
            )
        assert (
            serialized_tx.hex()
            == "03000200018dc5f38fcb801a6fad31de622a226e5b1886b1fecac41ada087d5c23be016e69010000006a47304402202d583f35f2dadaf252826d05d4404a74c3ed6405d1ca02d5969debc118aca0290220393bc5db057cc9860c4ea237d9672da63e0c34d424bb0e422a8557d78f10d8e80121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0186a4c872170000001976a914a579388225827d9f2fe9014add644487808c695d88ac00000000b5010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a13900000000000000000000ffffc6c74af14e1f00c3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a50006eb32f14e5da95f1fbd56f49d0f1cf44e4aafc7f595c258937a37ab3ca5b9faa7857d7e382eb64731b733fdba899c5418f4b11f05e3b129c53db2bb3f4d94bc100cdce626e712055eb79cb2448a084e52f25c62c28259bd3323302faa29b6f8"
        )

    def test_send_dash_dip2_proupregtx(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=100709999750,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "e4010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a13900000efda51589f86e30cc2305e7388c01ce0309c19a182cf37bced97c7da72236f660c0a395e765e6e06962ecff5a69d7de359c348a574176c210c37a25d4ffd917866fb0a31976a914e54445646929fac8b7d6c71715913af44324978488acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a5004120cb023e7f8babf92be0e91169da794cb204750ccb8ebe599495c04f720e3f932b6bb5384513541f17524ea7595f60fea00d483eaecc68d07caa6b99d7c605d637"
            )
        proregtx_id = bytes.fromhex(
            "39a1339d9bf26de701345beecc5de75a690bc9533741a3dbe90f2fd88b8ed461"
        )
        txdata = proto.SignTx()
        txdata.version = (3 << 16) | 3
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=221,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=proregtx_id),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=277,
                            extra_data_offset=0,
                            tx_hash=proregtx_id
                        ),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=221,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=221,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1], details=txdata,
                prev_txes=TX_API, extra_payload=extra_payload,
                external_txes=[proregtx_id]
            )
        assert (
            serialized_tx.hex()
            == "03000300018dc5f38fcb801a6fad31de622a226e5b1886b1fecac41ada087d5c23be016e69010000006b48304502210099fec2235397da1d802cca906c9e7a28c0454f0c96d58ae0bab5b8c90d1f5a73022034d820259303449512e97c8ca976841de4aabbf2f02f7d6b019034a4d1bc44840121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0186a4c872170000001976a914a579388225827d9f2fe9014add644487808c695d88ac00000000e4010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a13900000efda51589f86e30cc2305e7388c01ce0309c19a182cf37bced97c7da72236f660c0a395e765e6e06962ecff5a69d7de359c348a574176c210c37a25d4ffd917866fb0a31976a914e54445646929fac8b7d6c71715913af44324978488acc3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a5004120cb023e7f8babf92be0e91169da794cb204750ccb8ebe599495c04f720e3f932b6bb5384513541f17524ea7595f60fea00d483eaecc68d07caa6b99d7c605d637"
        )

    def test_send_dash_dip2_prouprevtx(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            amount=100709999750,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "a4010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a1390000c3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a500183721a5870eded00d0cd39905d3dc0bfaf30a69e8c3e40c2cc5478f5d8f058b4471ff1f64180145d6f4c54f7562676a00a0751a10d806bd06338fb06af4b53e51c2a47642ab91f9ad28ab66309669bdc9c82fa8a958256f156a5e4657000ab0"
            )
        proregtx_id = bytes.fromhex(
            "39a1339d9bf26de701345beecc5de75a690bc9533741a3dbe90f2fd88b8ed461"
        )
        txdata = proto.SignTx()
        txdata.version = (4 << 16) | 3
        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=inp1.prev_hash),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=inp1.prev_hash
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=157,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=proregtx_id),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=157,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=8,
                            extra_data_offset=0,
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXEXTRADATA,
                        details=proto.TxRequestDetailsType(
                            extra_data_len=157,
                            extra_data_offset=8,
                        ),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1], details=txdata,
                prev_txes=TX_API, extra_payload=extra_payload,
                external_txes=[proregtx_id]
            )
        assert (
            serialized_tx.hex()
            == "03000400018dc5f38fcb801a6fad31de622a226e5b1886b1fecac41ada087d5c23be016e69010000006b483045022100ae899bab721ade91116e903617988ffbcb2ef7bf307331dc1221768a4752778702202e057237b5ef239900c5a5c2f68e603c746445fb71d0756c70e4dc0486557af80121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0186a4c872170000001976a914a579388225827d9f2fe9014add644487808c695d88ac00000000a4010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a1390000c3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a500183721a5870eded00d0cd39905d3dc0bfaf30a69e8c3e40c2cc5478f5d8f058b4471ff1f64180145d6f4c54f7562676a00a0751a10d806bd06338fb06af4b53e51c2a47642ab91f9ad28ab66309669bdc9c82fa8a958256f156a5e4657000ab0"
        )

    def test_send_dash_dip2_external_output(self):
        self.setup_mnemonic_allallall()
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/1'/0'/0/0"),
            # dash testnet:ybQPZRHKifv9BDqMN2cieCsMzQQ1BuDoR5
            amount=100710000000,
            prev_hash=bytes.fromhex(
                "696e01be235c7d08da1ac4cafeb186185b6e222a62de31ad6f1a80cb8ff3c58d"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="yRdup9c8LRhvsK1CY1VVMFrEjPofCS5gSE",
            amount=100709999750,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        extra_payload = bytes.fromhex(
                "a4010061d48e8bd82f0fe9dba3413753c90b695ae75dccee5b3401e76df29b9d33a1390000c3803e9de251fdfe2f6fa200638ae4675511ec0bf0180983ea7a0ab2acd7a500183721a5870eded00d0cd39905d3dc0bfaf30a69e8c3e40c2cc5478f5d8f058b4471ff1f64180145d6f4c54f7562676a00a0751a10d806bd06338fb06af4b53e51c2a47642ab91f9ad28ab66309669bdc9c82fa8a958256f156a5e4657000ab0"
            )
        proregtx_id = bytes.fromhex(
            "39a1339d9bf26de701345beecc5de75a690bc9533741a3dbe90f2fd88b8ed461"
        )
        txdata = proto.SignTx()
        txdata.version = (4 << 16) | 3

        with pytest.raises(Cancelled) as exc:
            btc.sign_tx(
                self.client, "Dash Testnet", [inp1], [out1], details=txdata,
                prev_txes=TX_API, extra_payload=extra_payload,
                external_txes=[proregtx_id]
            )

