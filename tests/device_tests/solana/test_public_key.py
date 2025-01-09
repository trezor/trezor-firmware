# This file is part of the Trezor project.
#
# Copyright (C) 2012-2023 SatoshiLabs and contributors
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

from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.solana import get_public_key
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.solana,
    pytest.mark.models("core"),
]


@parametrize_using_common_fixtures(
    "solana/get_public_key.json",
)
def test_solana_get_public_key(client: Client, parameters, result):
    actual_result = get_public_key(
        client, address_n=parse_path(parameters["path"]), show_display=True
    )

    assert actual_result.hex() == result["expected_public_key"]
