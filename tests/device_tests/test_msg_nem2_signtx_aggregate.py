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

from trezorlib import nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2SignTxAggregate:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_aggregate_transfer_and_mosaic_definition(self, client):
        tx = nem2.sign_tx(
            client,
            # TODO: update to use m/44'/43'/0' and re-enable check in core/src/apps/nem2/validators
            # this will change the sign_tx payload
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_AGGREGATE_COMPLETE,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113728610090",
                "innerTransactions": [
                    {
                        "network": nem2.NETWORK_TYPE_TEST_NET,
                        "type": nem2.TYPE_TRANSACTION_TRANSFER,
                        "version": 38913,
                        "publicKey": "778D0B0CF67E361BE774AF22FA27B29C82FE6A9160537EB6A6D9C6ABE4796778",
                        "recipientAddress": {
                            "address": "TB6YHDGPYV3TGEFE7Z3BH2EXJZNVJJTH3EWL76PD",
                            "networkType": nem2.NETWORK_TYPE_TEST_NET
                        },
                        "message": {
                            "payload": "send 100 cat.currency to distributor",
                            "type": 0
                        },
                        "mosaics": [
                            {
                                "id": "9adf3b117a3c10ca",
                                "amount": "100"
                            }
                        ]
                    },
                    {
                        "network": nem2.NETWORK_TYPE_TEST_NET,
                        "type": nem2.TYPE_MOSAIC_DEFINITION,
                        "version": 38913,
                        "publicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
                        "mosaicId": "3F127E74B309F220",
                        "duration": 123,
                        "nonce": 3095715558,
                        "flags": 7,
                        "divisibility": 100
                    }
                ]
            },
        )

        assert (
            tx.payload.hex().upper()
            == "78010000000000006FE2D94CD1EB711A144BE51462BF5072696C2A384A90D0AD671EB1B11D3E6227E7A2007E5432BCC67A431938778C2957FC6827A28A18B02BC0C5FE6493030C02252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317000000000198414164000000000000002ADFC07A1A00000062760BDF210A8872A224A384F93CB0DC144CE372841573173048B6BEFD43184FD0000000000000008500000000000000778D0B0CF67E361BE774AF22FA27B29C82FE6A9160537EB6A6D9C6ABE47967780000000001985441987D838CCFC5773310A4FE7613E8974E5B54A667D92CBFF9E301250000000000CA103C7A113BDF9A64000000000000000073656E6420313030206361742E63757272656E637920746F206469737472696275746F720000004600000000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A62970000000001984D4120F209B3747E123F7B00000000000000E6DE84B807640000"
        )
        assert (
            tx.hash.hex().upper()
            == "713A409A55B1217E135AFBC4169BA1A97924C858CED677E504DEEB1219FD759F"
        )
