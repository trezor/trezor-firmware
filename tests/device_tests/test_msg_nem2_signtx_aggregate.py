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
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_AGGREGATE_BONDED,
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
                ],
                "cosignatures": [
                    {
                        "signature": "BBCD0639DD66E90F0C828FB76938B32DBD501173740F315D3BAD45804184B6CF843E4553F3177E3394992E6C893ADF1026394CCD05DD647EC6E00BB1B3843300",
                        "publicKey": "778D0B0CF67E361BE774AF22FA27B29C82FE6A9160537EB6A6D9C6ABE4796778"
                    },
                    {
                        "signature": "7EDBB4A981007E6BFEBFF8018FB7941A4C9583805E6560D725E3B53A6FE7BA1BA24567E5EC994300575176B39C56ABFEC1C75C45749896E6FDE3BEE315C1E70C",
                        "publicKey": "A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500"
                    }
                ]
            },
        )

        assert (
            tx.payload.hex().upper()
            == "380200000000000029CDA4BC3CC5CCE3FEA8BFB18620F5734DB197BDAA56284268798DCF395042CC7FB89506AA27AC5D95F44DD453067B7FE1439C336889459CE42CF376D6021306A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000198414264000000000000002ADFC07A1A00000062760BDF210A8872A224A384F93CB0DC144CE372841573173048B6BEFD43184FD0000000000000008500000000000000778D0B0CF67E361BE774AF22FA27B29C82FE6A9160537EB6A6D9C6ABE47967780000000001985441987D838CCFC5773310A4FE7613E8974E5B54A667D92CBFF9E301250000000000CA103C7A113BDF9A64000000000000000073656E6420313030206361742E63757272656E637920746F206469737472696275746F720000004600000000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A62970000000001984D4120F209B3747E123F7B00000000000000E6DE84B807640000778D0B0CF67E361BE774AF22FA27B29C82FE6A9160537EB6A6D9C6ABE4796778BBCD0639DD66E90F0C828FB76938B32DBD501173740F315D3BAD45804184B6CF843E4553F3177E3394992E6C893ADF1026394CCD05DD647EC6E00BB1B3843300A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715007EDBB4A981007E6BFEBFF8018FB7941A4C9583805E6560D725E3B53A6FE7BA1BA24567E5EC994300575176B39C56ABFEC1C75C45749896E6FDE3BEE315C1E70C"
        )
        assert (
            tx.hash.hex().upper()
            == "6B819F85494A366D2034B55398C4EC087CA9B33771DEC685980A233E09FF2950"
        )
