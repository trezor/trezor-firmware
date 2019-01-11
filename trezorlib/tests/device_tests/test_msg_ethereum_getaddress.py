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

from trezorlib import ethereum
from trezorlib.tools import H_

from .common import TrezorTest


@pytest.mark.ethereum
class TestMsgEthereumGetaddress(TrezorTest):
    def test_ethereum_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            ethereum.get_address(self.client, [H_(44), H_(60)]).hex()
            == "e025dfbe2c53638e547c6487ded34add7b8aafc1"
        )
        assert (
            ethereum.get_address(self.client, [H_(44), H_(60), 1]).hex()
            == "ed46c856d0c79661cf7d40ffe0c0c5077c00e898"
        )
        assert (
            ethereum.get_address(self.client, [H_(44), H_(60), 0, H_(1)]).hex()
            == "6682fa7f3ec58581b1e576268b5463b4b5c93839"
        )
        assert (
            ethereum.get_address(self.client, [H_(44), H_(60), H_(9), 0]).hex()
            == "fb3be0f9717ff5fcf3c58eb49a9ed67f1bd89d4e"
        )
        assert (
            ethereum.get_address(self.client, [H_(44), H_(60), 0, 9999999]).hex()
            == "6b909b50d88c9a8e02453a87b3662e3e7a5e0cf1"
        )
        assert (
            ethereum.get_address(self.client, [H_(44), H_(6060), 0, 9999999]).hex()
            == "98b8e926bd224764de2a0e4f4cbe1521474050af"
        )
