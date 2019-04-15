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

from trezorlib.tezos import get_address
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.tezos
@pytest.mark.skip_t1
class TestMsgTezosGetAddress(TrezorTest):
    def test_tezos_get_address(self):
        self.setup_mnemonic_allallall()

        path = parse_path("m/44'/1729'/0'")
        address = get_address(self.client, path, show_display=True)
        assert address == "tz1Kef7BSg6fo75jk37WkKRYSnJDs69KVqt9"

        path = parse_path("m/44'/1729'/1'")
        address = get_address(self.client, path, show_display=True)
        assert address == "tz1ekQapZCX4AXxTJhJZhroDKDYLHDHegvm1"
