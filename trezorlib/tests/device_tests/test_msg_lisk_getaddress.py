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

from trezorlib import lisk
from trezorlib.tools import parse_path

from .common import TrezorTest

LISK_PATH = parse_path("m/44h/134h/0h/1h")


@pytest.mark.lisk
class TestMsgLiskGetaddress(TrezorTest):
    def test_lisk_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert lisk.get_address(self.client, LISK_PATH[:2]) == "1431530009238518937L"
        assert lisk.get_address(self.client, LISK_PATH[:3]) == "17563781916205589679L"
        assert lisk.get_address(self.client, LISK_PATH) == "1874186517773691964L"
        assert (
            lisk.get_address(self.client, parse_path("m/44h/134h/999h/999h"))
            == "16295203558710684671L"
        )
