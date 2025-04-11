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

from trezorlib import nem
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.nem
@pytest.mark.models("t1b1", "t2t1")
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
@pytest.mark.parametrize("chunkify", (True, False))
def test_nem_getaddress(client: Client, chunkify: bool):
    assert (
        nem.get_address(
            client,
            parse_path("m/44h/1h/0h/0h/0h"),
            0x68,
            show_display=True,
            chunkify=chunkify,
        )
        == "NB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQGHUBWQN"
    )
    assert (
        nem.get_address(
            client,
            parse_path("m/44h/1h/0h/0h/0h"),
            0x98,
            show_display=True,
            chunkify=chunkify,
        )
        == "TB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQHSBNBMF"
    )
