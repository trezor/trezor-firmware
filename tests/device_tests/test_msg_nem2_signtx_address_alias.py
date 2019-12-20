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

from trezorlib import messages as proto, nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2SignTxAddressAlias:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_link_address_alias(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ADDRESS_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_LINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "address": {
                    "address": "TDUIDV5CRFYLZMOEVJBGPHEIRVJFAADIDY2HPTOS",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A20000000000000082DBA6A556DCFAFCA1BF5C4691483260C83F3286C69925DB6BC7FD7911D1DA7E7715F72D275B08E454E42F9281F867E28EF96B9BC5E4CB42EA5E90981772BE03A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984E42204E000000000000090A1E5E1A00000067CBDB6208CBA4EA98E881D7A28970BCB1C4AA42679C888D525000681E3477CDD201"
        )

        assert (
            tx.hash.hex().upper()
            == "B0ED7036511388949625D4B253E362912F944C83ECA54DBE8718151BA3BB841E"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_unlink_address_alias(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ADDRESS_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_UNLINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "address": {
                    "address": "TDUIDV5CRFYLZMOEVJBGPHEIRVJFAADIDY2HPTOS",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A2000000000000004F2F0EC381069C101C5589D9E475A9EA95814CA6E99FE627605D4A0245D3374FB489761A8254B43A5DDD881A89F2B28848BA6964139A1D79E44C03A25F32EA0EA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984E42204E000000000000090A1E5E1A00000067CBDB6208CBA4EA98E881D7A28970BCB1C4AA42679C888D525000681E3477CDD200"
        )

        assert (
            tx.hash.hex().upper()
            == "BCDBB6150C2FF7F85EC01F533FA79B27F02CDE85182BB57453E8C89FA1A576CC"
        )