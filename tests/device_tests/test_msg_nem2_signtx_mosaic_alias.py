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
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_LINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "mosaicId": "4ADB6668071C4969"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "91000000000000003FE855E3ED1412EA041A85702D6B3F3FBAF9F6DE1D89F730E4FB7F53630B614BD3B15E219F23FDB65034AF799B927A64D67F50CD15C2017FC2E5F2E85F28B908252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984E43204E000000000000090A1E5E1A00000067CBDB6208CBA4EA69491C076866DB4A01"
        )

        assert (
            tx.hash.hex().upper()
            == "FCBAA4A4156F2E7F1F516375786D4E8F6D5C13CA5B23C7195B6E787E21B8649C"
        )