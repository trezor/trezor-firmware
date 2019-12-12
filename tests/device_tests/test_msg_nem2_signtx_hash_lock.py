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
class TestMsgNEM2SignTxHashLock:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_hash_lock(self, client):

        # If you uncomment the code below, and configure with the you desired paramters,
        # you can use the hash returned from the aggregate transaction test in the hash lock
        # test, just access it through signed_aggregate_tx.hash.hex().upper()

        # signed_aggregate_tx = nem2.sign_tx(
        #     client,
        #     parse_path("m/44'/43'/0'/0'/0'"),
        #     "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
        #     {
        #         "type": nem2.TYPE_AGGREGATE_COMPLETE,
        #         "network": nem2.NETWORK_TYPE_MIJIN_TEST,
        #         "version": 36865,
        #         "maxFee": "100",
        #         "deadline": "113728610090",
        #         "innerTransactions": [
        #             {
        #                 "network": nem2.NETWORK_TYPE_MIJIN_TEST,
        #                 "type": nem2.TYPE_TRANSACTION_TRANSFER,
        #                 "version": 36865,
        #                 "publicKey": "BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD",
        #                 "recipientAddress": {
        #                     "address": "SAAXKRVD6HLAN6IHYM7YWTS3W2BGYXCRBNSA4Q6Y",
        #                     "networkType": nem2.NETWORK_TYPE_MIJIN_TEST
        #                 },
        #                 "message": {
        #                     "payload": "send 100 cat.currency to distributor",
        #                     "type": 0
        #                 },
        #                 "mosaics": [
        #                     {
        #                         "id": "9adf3b117a3c10ca",
        #                         "amount": "100"
        #                     }
        #                 ]
        #             },
        #             {
        #                 "network": nem2.NETWORK_TYPE_MIJIN_TEST,
        #                 "type": nem2.TYPE_MOSAIC_DEFINITION,
        #                 "version": 36865,
        #                 "publicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
        #                 "mosaicId": "3F127E74B309F220",
        #                 "duration": 123,
        #                 "nonce": 3095715558,
        #                 "flags": 7,
        #                 "divisibility": 100
        #             }
        #         ]
        #     },
        # )

        signed_hash_lock_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_HASH_LOCK,
                "network": nem2.NETWORK_TYPE_MIJIN_TEST,
                "version": 36865,
                "maxFee": "0",
                "deadline": "113728610090",
                "mosaic": {
                    "amount": "10000000",
                    "id": "85BBEA6CC462B244"
                },
                "duration": "480",
                "hash": "4FF8C7E00B02D7380900B7795B4CDDC5B9D03536B5BD896BF54F8E5C53F4A32B"
            },
        )

        assert (
            signed_hash_lock_tx.payload.hex().upper()
            == "B800000000000000B8A4B2F9CC46839DBCBF85577CD99B4F1B1A5AD1DBCCF405A2D6005F72AB702758CF09045C5B83AB2E3DC38084171DDCD57D6A4BF27A797FC425D3071B36F60EA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000190484100000000000000002ADFC07A1A00000044B262C46CEABB858096980000000000E0010000000000004FF8C7E00B02D7380900B7795B4CDDC5B9D03536B5BD896BF54F8E5C53F4A32B"
        )
        assert (
            signed_hash_lock_tx.hash.hex().upper()
            == "36398BE11F57CF56A3AB65BD70AE19480FB0CBB093B2A3CD62646DD0123B5320"
        )
