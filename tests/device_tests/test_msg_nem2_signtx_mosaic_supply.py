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
class TestMsgNEM2SignTxMosaicSupply:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_supply(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_SUPPLY_CHANGE,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113728610090",
                "mosaicId": "4ADB6668071C4969",
                "action": 1,
                "delta": "1000000"
            },
        )

        assert (
            tx.payload.hex().upper()
            == "9100000000000000DA04A20F41130A0003F99829042B674840C94331307D833E921244F66AA0096E035B685B4131D8BC9DD515CD0D0F2529A2DFC48FDC61EFE1A38A8B16ED110106252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984D4264000000000000002ADFC07A1A00000069491C076866DB4A40420F000000000001"
        )
        assert (
            tx.hash.hex().upper()
            == "3103637EAC6D5847E304AC35CC7BCB2881E06C271E370A7B513F221C59F00ADC"
        )