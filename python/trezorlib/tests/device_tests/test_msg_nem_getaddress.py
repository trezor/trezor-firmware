# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.nem
class TestMsgNEMGetaddress(TrezorTest):
    def test_nem_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            nem.get_address(self.client, parse_path("m/44'/1'/0'/0'/0'"), 0x68)
            == "NB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQGHUBWQN"
        )
        assert (
            nem.get_address(self.client, parse_path("m/44'/1'/0'/0'/0'"), 0x98)
            == "TB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQHSBNBMF"
        )
