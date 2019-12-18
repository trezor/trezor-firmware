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
class TestMsgNEM2GetPublicKey:

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_get_public_key(self, client):
        assert (
            nem2.get_public_key(client, parse_path("m/44'/43'/0'/0'/0'"), False).public_key.hex().upper()
            == "A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_get_public_key_with_display(self, client):
        assert (
            nem2.get_public_key(client, parse_path("m/44'/43'/0'/0'/0'"), True).public_key.hex().upper()
            == "A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500"
        )
