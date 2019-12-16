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
class TestMsgNEM2SignTxAccountMosaicRestriction:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_account_mosaic_restriction(self, client):
        signed_account_mosaic_restriction_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ACCOUNT_MOSAIC_RESTRICTION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",
                "restrictionType": nem2.ACCOUNT_RESTRICTION_BLOCK_MOSAIC,
                "restrictionAdditions": ["9ADF3B117A3C10CA"],
                "restrictionDeletions": []
            },
        )

        assert (
            signed_account_mosaic_restriction_tx.payload.hex().upper()
            == "900000000000000072D2333B6C68EA9FEEAD826197B80B30695F45480AFFB3CDD057CEDA4923B488D1A2AE68234FE2335BA2353DD7A0860BF635B6A3DFE7DAF18622F0F19703C40C252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF31700000000019850420000000000000000090A1E5E1A0000000280010000000000CA103C7A113BDF9A"
        )
        assert (
            signed_account_mosaic_restriction_tx.hash.hex().upper()
            == "69AC70AFFF8F2251481C7AABEA3C87C04F40C53B209178C1EF9DCF3CCA2DEE05"
        )
