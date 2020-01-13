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
class TestMsgNEM2SignTxAccountLink:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_account_link(self, client):
        signed_account_link_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ACCOUNT_LINK,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",                
                "remotePublicKey": "51585DA12749432888AC492B4D3AB7E5AAC0108773ED12A01EC8EB8EECA1D820",
                "linkAction": 1
            },
        )

        assert (
            signed_account_link_tx.payload.hex().upper()
            == "A10000000000000076B7A30F81BCCD8EA1A78443C94655D21DA7616E53B510452548C4A356C4D21EF0440AE323AF051C6E4DCC613ED26CAFA877B32A85F8D2B9733CE46707298A0FA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984C410000000000000000090A1E5E1A00000051585DA12749432888AC492B4D3AB7E5AAC0108773ED12A01EC8EB8EECA1D82001"
        )
        assert (
            signed_account_link_tx.hash.hex().upper()
            == "4F8DE81E9B896C299E16B1CFBB71F9109D4464046876FAC857BEF8CE5147E0E7"
        )
