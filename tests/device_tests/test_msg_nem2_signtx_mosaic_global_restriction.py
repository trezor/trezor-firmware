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
class TestMsgNEM2SignTxMosaicGlobalRestriction:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_global_restriction(self, client):
        signed_global_restriction_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_GLOBAL_RESTRICTION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",                
                "mosaicId": "0DC67FBE1CAD29E3",
                "referenceMosaicId": "0B65C4B29A80C619",
                "restrictionKey": "0000000000000457",
                "previousRestrictionValue": "1",
                "previousRestrictionType": 1,
                "newRestrictionValue": "2",
                "newRestrictionType": 1
            },
        )

        assert (
            signed_global_restriction_tx.payload.hex().upper()
            == "AA0000000000000053D75E97D1386E8E5A60919F5A1CC6E776DCC2B9CFF1BC484E0E1BBF9A4C8C22EA77E67D48A22749D88F8EDD0E7D4E8F5685E944AB543BBA38DAD9477C1A8D01A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019851410000000000000000090A1E5E1A000000E329AD1CBE7FC60D19C6809AB2C4650B5704000000000000010000000000000002000000000000000101"
        )
        assert (
            signed_global_restriction_tx.hash.hex().upper()
            == "0837D6B16A1BF9C6BA771A1CECD9CBFFF44D980D7AA6BA7CB9BED2C7A3B35C6D"
        )
