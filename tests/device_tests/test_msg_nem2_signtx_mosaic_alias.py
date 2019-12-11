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
class TestMsgNEM2SignTxMosaicAlias:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_link_mosaic_alias(self, client):
        tx = nem2.sign_tx(
            client,
            # TODO: update to use m/44'/43'/0' and re-enable check in core/src/apps/nem2/validators
            # this will change the sign_tx payload
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_LINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "mosaicId": "0B65C4B29A80C619"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "9100000000000000D41550C1996C2CA450B4AF37F5003FAEA35A53B638B2007882004FEB6093F5C774F69D94250F5E97E9C24AFD62ACA234E9155B4E18F9E1609168DA8329CC9206A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984E43204E000000000000090A1E5E1A00000067CBDB6208CBA4EA19C6809AB2C4650B01"
        )

        assert (
            tx.hash.hex().upper()
            == "694A140811AA0AA6EB1B23076C4117D9F59DE0EA407B80588A05C1B084872912"
        )