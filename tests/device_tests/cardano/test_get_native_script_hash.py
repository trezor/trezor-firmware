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

from trezorlib import messages
from trezorlib.cardano import get_native_script_hash, parse_native_script

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]


@parametrize_using_common_fixtures(
    "cardano/get_native_script_hash.json",
)
def test_cardano_get_native_script_hash(client, parameters, result):
    client.init_device(new_session=True, derive_cardano=True)

    native_script_hash = get_native_script_hash(
        client,
        native_script=parse_native_script(parameters["native_script"]),
        display_format=messages.CardanoNativeScriptHashDisplayFormat.__members__[
            parameters["display_format"]
        ],
    ).script_hash

    assert native_script_hash.hex() == result["expected_hash"]
