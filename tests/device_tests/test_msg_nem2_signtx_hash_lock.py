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
        #         "network": nem2.NETWORK_TYPE_TEST_NET,
        #         "version": 36865,
        #         "maxFee": "100",
        #         "deadline": "113728610090",
        #         "innerTransactions": [
        #             {
        #                 "network": nem2.NETWORK_TYPE_TEST_NET,
        #                 "type": nem2.TYPE_TRANSACTION_TRANSFER,
        #                 "version": 36865,
        #                 "publicKey": "BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD",
        #                 "recipientAddress": {
        #                     "address": "SAAXKRVD6HLAN6IHYM7YWTS3W2BGYXCRBNSA4Q6Y",
        #                     "networkType": nem2.NETWORK_TYPE_TEST_NET
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
        #                 "network": nem2.NETWORK_TYPE_TEST_NET,
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
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113728610090",
                "mosaic": {
                    "amount": "10000000",
                    "id": "85BBEA6CC462B244"
                },
                "duration": "480",
                "hash": "6B819F85494A366D2034B55398C4EC087CA9B33771DEC685980A233E09FF2950"
            },
        )

        assert (
            signed_hash_lock_tx.payload.hex().upper()
            == "B800000000000000804B3A352A5C4BD6F66F2BBEAC2DDD88D922C10D83099195B1A8F7CF4F3E5A73D91780C53170920B2982648FA246BA9A8AE6C1A126ADC41B23AA4E5970099B05A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000198484100000000000000002ADFC07A1A00000044B262C46CEABB858096980000000000E0010000000000006B819F85494A366D2034B55398C4EC087CA9B33771DEC685980A233E09FF2950"
        )
        assert (
            signed_hash_lock_tx.hash.hex().upper()
            == "C2E77A746B6E68A8253D696DCE2EBC5B6D5E7E2B04C8618B1D7E60FEDFF6F6EC"
        )
