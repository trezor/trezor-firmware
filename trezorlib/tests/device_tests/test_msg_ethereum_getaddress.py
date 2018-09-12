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
            ethereum.get_address(self.client, []).hex()
            == "1d1c328764a41bda0492b66baa30c4a339ff85ef"
        )
        assert (
            ethereum.get_address(self.client, [1]).hex()
            == "437207ca3cf43bf2e47dea0756d736c5df4f597a"
        )
        assert (
            ethereum.get_address(self.client, [0, H_(1)]).hex()
            == "e5d96dfa07bcf1a3ae43677840c31394258861bf"
        )
        assert (
            ethereum.get_address(self.client, [H_(9), 0]).hex()
            == "f68804ac9eca9483ab4241d3e4751590d2c05102"
        )
        assert (
            ethereum.get_address(self.client, [0, 9999999]).hex()
            == "7a6366ecfcaf0d5dcc1539c171696c6cdd1eb8ed"
        )
