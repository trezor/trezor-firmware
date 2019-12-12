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
class TestMsgNEM2SignTxMosaics:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_definition(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_DEFINITION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113728610090",
                "nonce": 3095715558,
                "mosaicId": "4ADB6668071C4969",
                "flags": 7,
                "divisibility": 100,
                "duration": "123"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "9600000000000000B77D746E5440126CB63B20E39287D922D8F968197320C8FEACAEAC0251FBD9BFBCDE1E82D6DABF11E1998622B0ADB4B7C2771AF1647E923A9F30FFF1F0E1B102252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984D4164000000000000002ADFC07A1A00000069491C076866DB4A7B00000000000000E6DE84B80764"
        )
        assert (
            tx.hash.hex().upper()
            == "3860DD7473B4BD7BA156A7891273E5FDC004594666D0CC14B8146F808E29CA35"
        )
