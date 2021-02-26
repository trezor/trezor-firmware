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

from trezorlib import solana
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.solana
@pytest.mark.parametrize(
    "path, address",
    (
        ("m/44h/501h/0h", "4UR47Kp4FxGJiJZZGSPAzXqRgMmZ27oVfGhHoLmcHakE"),
        ("m/44h/501h/1h", "GQGPHxNcyoaGUzEyxHMJHXrF4DSWeeg4FXP7dhswL2cW"),
        ("m/44h/501h/100h", "3Ja3k27nJHZmNPKDkzumakTdKGZj9cekoScUgP5v6jZ5"),
    ),
)
def test_solana_getaddress(client, path, address):
    address_n = parse_path(path)
    assert solana.get_address(client, address_n) == address
