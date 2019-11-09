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
            parse_path("m/44'/43'/0'/0'/0'"),
            {
                "type": nem2.TYPE_MOSAIC_DEFINITION,
                "network_type": nem2.NETWORK_TYPE_TEST_NET,
                "generation_hash": "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
                "version": 38913,
                "max_fee": "100",
                "deadline": "113728610090",
                "nonce": 3095715558,
                "mosaic_id": "57319AF73440C323",
                "flags": 7,
                "divisibility": 100,
                "duration": "123"
            },
        )

        assert (
            tx.payload.hex().upper()
            == "8E000000853683E02F7651AFBD6905CE23B9F4C9FB25559F2B89EE1892F7B3062C56FDAF898C6E9E7A3005BDF518AB8BA4D9E40248ACDB80E952F046DCA497C5FEEEE7028AF53BB8F3A167C68F264C33237DB309DBC88F64D7A1088B8BEEA5A34DBBBEC201984D4164000000000000002ADFC07A1A000000E6DE84B823C34034F79A315707647B00000000000000"
        )
        # == "E6DE84B823C34034F79A315707000000000000000000"
        # assert (
        #     tx.hash.hex()
        #     == "533E8FB484BF73A1E401BE2B028A5962BD37E277C1BC168F77214DB08C0D7106"
        # )