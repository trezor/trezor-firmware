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
class TestMsgNEM2SignTxAccountAddressRestriction:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_account_address_restriction(self, client):
        signed_account_address_restriction_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ACCOUNT_ADDRESS_RESTRICTION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",
                "restrictionType": nem2.ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS,
                "restrictionAdditions": [
                    {
                        "address": "TBXH7SBBRXI4BECXRXR54VIRZR34YN75LZ3ZRRC3",
                        "networkType": nem2.NETWORK_TYPE_TEST_NET
                    }
                ],
                "restrictionDeletions": [
                    {
                        "address": "TBRL2IM33LWRHIDNVMO6M6LPBQ2CUS67KI7XJDCZ",
                        "networkType": nem2.NETWORK_TYPE_TEST_NET
                    },
                    {
                        "address": "TAWIV4Y5YACUYEP3BPCGS27ERBPOF34CVZXYYZN7",
                        "networkType": nem2.NETWORK_TYPE_TEST_NET
                    }
                ]
            },
        )

        assert (
            signed_account_address_restriction_tx.payload.hex().upper()
            == "D3000000000000002B7B6FE5B8C2AB86A0EC9C4B9B64E814D90541A08CF6FC8B76F5F0072FC7A4E20CEAEB462874F7BBE651E0B9DD95E695391E716044D72D9DAF36BA8313694C08A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019850410000000000000000090A1E5E1A0000000100010200000000986E7FC8218DD1C090578DE3DE5511CC77CC37FD5E7798C45B9862BD219BDAED13A06DAB1DE6796F0C342A4BDF523F748C59982C8AF31DC0054C11FB0BC4696BE4885EE2EF82AE6F8C65BF"
        )
        assert (
            signed_account_address_restriction_tx.hash.hex().upper()
            == "819294D9B161FD86BD9E459AB64874B2358F8375CA94E7141FFAF944DFA4CDED"
        )
