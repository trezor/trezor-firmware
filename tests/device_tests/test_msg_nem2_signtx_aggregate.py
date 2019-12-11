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
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_AGGREGATE_COMPLETE,
                "network": nem2.NETWORK_TYPE_MIJIN_TEST,
                "version": 36865,
                "maxFee": "100",
                "deadline": "113728610090",
                "innerTransactions": [
                    {
                        "network": nem2.NETWORK_TYPE_MIJIN_TEST,
                        "type": nem2.TYPE_TRANSACTION_TRANSFER,
                        "version": 36865,
                        "publicKey": "BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD",
                        "recipientAddress": {
                            "address": "SAAXKRVD6HLAN6IHYM7YWTS3W2BGYXCRBNSA4Q6Y",
                            "networkType": nem2.NETWORK_TYPE_MIJIN_TEST
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
                        "network": nem2.NETWORK_TYPE_MIJIN_TEST,
                        "type": nem2.TYPE_MOSAIC_DEFINITION,
                        "version": 36865,
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
            == "78010000000000001372FAFF5748AEA21C67138EDE6A118FF639606D534B955CFCB09DD2688E9F900C3180A14343A47F05526478B8011C984C189A05113C79D0BEBB6EB2FFA7AC0BA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000190414164000000000000002ADFC07A1A000000E114E6428F83FE97E532F4698A4181B2BE859850CA43E63D7BBB0E73AA6850BBD0000000000000008500000000000000BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD000000000190544190017546A3F1D606F907C33F8B4E5BB6826C5C510B640E43D801250000000000CA103C7A113BDF9A64000000000000000073656E6420313030206361742E63757272656E637920746F206469737472696275746F720000004600000000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A62970000000001904D4120F209B3747E123F7B00000000000000E6DE84B807640000"
        )
        assert (
            tx.hash.hex().upper()
            == "9B8CEF0FA37A0C15F9F3C831406C65152BDAE4C39BAAD753C67CDAF3DC430332"
        )
