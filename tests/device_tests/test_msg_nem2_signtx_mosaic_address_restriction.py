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
class TestMsgNEM2SignTxMosaicAddressRestriction:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_address_restriction(self, client):
        signed_address_restriction_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_ADDRESS_RESTRICTION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",                
                "mosaicId": "0DC67FBE1CAD29E3",
                "restrictionKey": "0000000000000457",
                "previousRestrictionValue": "1",
                "newRestrictionValue": "2",
                "targetAddress": {
                    "address": "TCOYOMZ3LEF6ZCHCNKEWLVTYCLSPUBSBTTAM6F2D",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                },
            },
        )

        assert (
            signed_address_restriction_tx.payload.hex().upper()
            == "B90000000000000012A9C2E77C12814A0C0E924687A189CEDC14C557C6291F0C59AA666B453C75D9BBF969DA55F9A7EFC3C95FB8EE85A3379D66E5EEDCD04A04DA3E213A12006A03A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019851420000000000000000090A1E5E1A000000E329AD1CBE7FC60D570400000000000001000000000000000200000000000000989D87333B590BEC88E26A8965D67812E4FA06419CC0CF1743"
        )
        assert (
            signed_address_restriction_tx.hash.hex().upper()
            == "3D8010ADE29B470C7324D58D113614446E7834D466842CF9B1433E3B4E8B7B28"
        )
