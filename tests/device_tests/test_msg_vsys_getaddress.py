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

from trezorlib.vsys import get_address
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.vsys
@pytest.mark.skip_t1
@pytest.mark.setup_client(
    mnemonic="split story lonely fat list exile lawsuit zero coffee airport dish disorder pattern only mention clock stand soul wage woman frown nut viable thought"
)
class TestMsgVsysGetAddress:
    def test_vsys_get_address(self, client):
        path = parse_path("m/44'/360'/0'")
        address = get_address(client, path, show_display=True)
        assert address == "ARJGXkS7nxK3TaYMQxvWs7WahwR2NJMQFBW"

        path = parse_path("m/44'/360'/1'")
        address = get_address(client, path, show_display=True)
        assert address == "AR4U6sFGSzH8XCHHjMU8Y9PAU9j8khXxy5B"

        path = parse_path("m/44'/1'/0'")
        address = get_address(client, path, show_display=True)
        assert address == "AUC89jnZnmGeNp3gLBcBofNC3e4u3DV4fxp"

        path = parse_path("m/44'/1'/1'")
        address = get_address(client, path, show_display=True)
        assert address == "ATwncwd63jAqF6B2NH8Zs2giMHgzXPSBtBk"
