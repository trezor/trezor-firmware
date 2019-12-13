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
class TestMsgNEM2SignTxAccountMetadata:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_account_metadata(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ACCOUNT_METADATA,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "targetPublicKey": "252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317",
                "scopedMetadataKey": "0000000000000001",
                "valueSizeDelta": 11,
                "valueSize": 11,
                "value": "41206E65772076616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "B70000000000000035E1F3AB3AE9812FB176A21F085EC1AB75B933B4D7CE3102A8005167A37A11A9405AAEC9148CFADEE607EFADA94888C9966830A70F0D894AA0B145A24AC3750C252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984441204E000000000000090A1E5E1A000000252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF31701000000000000000B000B0041206E65772076616C7565"
        )

        assert (
            tx.hash.hex().upper()
            == "09CE8CCDC2538476F8C5FB50CB241CC2EA22AE87BF507CC3317CA0B5A25B60A6"
        )