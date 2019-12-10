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

from trezorlib.vsys import get_public_key
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.vsys
@pytest.mark.skip_t1
@pytest.mark.setup_client(
    mnemonic="split story lonely fat list exile lawsuit zero coffee airport dish disorder pattern only mention clock stand soul wage woman frown nut viable thought"
)
class TestMsgVsysGetPublicKey:
    def test_vsys_get_public_key(self, client):
        path = parse_path("m/44'/360'/0'")
        pk = get_public_key(client, path)
        assert pk == "EJqSddw7JRvTkNTPkddWCmboa7rbQD8f4LAqngfhb6Hw"

        path = parse_path("m/44'/360'/1'")
        pk = get_public_key(client, path)
        assert pk == "HQGZrkdzZiGkD9RwBhDXiZzNqRJiiWqvViJSxcyGnPhV"
