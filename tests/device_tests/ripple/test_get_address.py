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

from trezorlib.ripple import get_address
from trezorlib.tools import parse_path

CUSTOM_MNEMONIC = (
    "armed bundle pudding lazy strategy impulse where identify "
    "submit weekend physical antenna flight social acoustic absurd "
    "whip snack decide blur unfold fiction pumpkin athlete"
)


@pytest.mark.altcoin
@pytest.mark.ripple
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgRippleGetAddress:
    def test_ripple_get_address(self, client):
        # data from https://iancoleman.io/bip39/
        address = get_address(client, parse_path("m/44'/144'/0'/0/0"))
        assert address == "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H"
        address = get_address(client, parse_path("m/44'/144'/0'/0/1"))
        assert address == "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws"
        address = get_address(client, parse_path("m/44'/144'/1'/0/0"))
        assert address == "rJX2KwzaLJDyFhhtXKi3htaLfaUH2tptEX"

    @pytest.mark.setup_client(mnemonic=CUSTOM_MNEMONIC)
    def test_ripple_get_address_other(self, client):
        # data from https://github.com/you21979/node-ripple-bip32/blob/master/test/test.js
        address = get_address(client, parse_path("m/44'/144'/0'/0/0"))
        assert address == "r4ocGE47gm4G4LkA9mriVHQqzpMLBTgnTY"
        address = get_address(client, parse_path("m/44'/144'/0'/0/1"))
        assert address == "rUt9ULSrUvfCmke8HTFU1szbmFpWzVbBXW"
