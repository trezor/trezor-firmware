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
class TestMsgNEM2SignTxAccountOperationRestriction:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_account_operation_restriction(self, client):
        signed_account_operation_restriction_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ACCOUNT_OPERATION_RESTRICTION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113248176649",
                "restrictionType": nem2.ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE,
                "restrictionAdditions": [nem2.TYPE_ACCOUNT_METADATA, nem2.TYPE_MOSAIC_ALIAS],
                "restrictionDeletions": [nem2.TYPE_HASH_LOCK]
            },
        )

        assert (
            signed_account_operation_restriction_tx.payload.hex().upper()
            == "8E000000000000003BDAF54D2E6EA7B904E07D38592E0BABB4E1E7410E672908A4BD37C84A7DC5E55A61288D00950BABA6EF8624CFD550F70E5DFD42188B6CD560A1209F5B4C2506252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF31700000000019850430000000000000000090A1E5E1A000000040002010000000044414E434841"
        )
        assert (
            signed_account_operation_restriction_tx.hash.hex().upper()
            == "FE8F450F2EE3BD6834222B2D9812D56EF62E0B6CBE59801B6A48B5202E3F170D"
        )
