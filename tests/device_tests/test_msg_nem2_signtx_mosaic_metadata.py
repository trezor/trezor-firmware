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
class TestMsgNEM2SignTxMosaicMetadata:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_metadata(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_METADATA,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "targetPublicKey": "A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500",
                "scopedMetadataKey": "0000000000000001",
                "valueSizeDelta": 11,
                "targetMosaicId": "9adf3b117a3c10ca",
                "valueSize": 11,
                "value": "41206E65772076616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BF0000000000000029FBB5B96A4621CB615775B3F84D56E73B596F4D856C56457FCA84B96F8724D38D462414B5C27AE2EDE16FB993BBAE76BB2EFDE1BB247F12D3CDDDF0BDD8A90DA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984442204E000000000000090A1E5E1A000000A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000100000000000000CA103C7A113BDF9A0B000B0041206E65772076616C7565"
        )

        assert (
            tx.hash.hex().upper()
            == "B4B2ACE7C2CCDA808359F3C9571C7A8F1D415598416C383BE76F7EF0EBF5D036"
        )