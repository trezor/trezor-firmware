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
            parse_path("m/44'/43'/0'/0'/0'"),
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
            == "90000000000000008D3AA94862524AF3456273A12FBA755C9462AFA8D517C2E9BDD109087207C03D1AAA0C1696903F45DEAB8863495B65C8CF6377F514FBA14A09FB496AC7B8B30FA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019850420000000000000000090A1E5E1A0000000280010000000000CA103C7A113BDF9A"
        )
        assert (
            signed_account_mosaic_restriction_tx.hash.hex().upper()
            == "1FC70E2BB941D38C334F01C05EF598BEA5EECE914308AE5488F534514A15A087"
        )
