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
class TestMsgNEM2SignTxCosign:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_cosign(self, client):
        cosigned_tx = nem2.cosign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            {
                "hash":"09CF3DB1DD3179065C3841F44021C403B831E7D11C11DA943CB926539B921CE5",
            },
        )

        assert (
            cosigned_tx.parent_hash.hex().upper()
            == "09CF3DB1DD3179065C3841F44021C403B831E7D11C11DA943CB926539B921CE5"
        )
        assert (
            cosigned_tx.signature.hex().upper()
            == "19955C1C4379DF5AC6784EE168C2EA35EED89BD0B170EAEE43E284BA49CB71B0B627DC3BB1DC84D582F686C7D618A5DFB383722C0167F27A8F63B9C0FE6E180C"
        )
