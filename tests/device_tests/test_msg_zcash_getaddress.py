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

from trezorlib import zcash
from trezorlib.tools import parse_path

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.zcash
@pytest.mark.skip_t1
class TestMsgZcashGetaddress:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_zcash_getaddress(self, client):
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/1h/0h/0/0"), show_display=True)
            == "tmF2pJ7nLJA8N7WjQiRyjTBWmUR1VztVHt1"
        )
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/133h/0h/0/0"), show_display=True)
            == "t1NKu7kH5nQNPu1JVh7FuPhAHyqKZRpnpBq"
        )
        # TODO: unified addresses