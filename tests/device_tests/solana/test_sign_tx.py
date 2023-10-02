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
from trezorlib.solana import sign_tx
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from .construct.instructions import INSTRUCTION_ID_FORMATS, replace_account_placeholders
from .construct.transaction import MESSAGE

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.solana,
    pytest.mark.skip_t1,
]


@parametrize_using_common_fixtures(
    "solana/sign_tx.system_program.json",
    "solana/sign_tx.stake_program.json",
    "solana/sign_tx.associated_token_account_program.json",
    "solana/sign_tx.memo_program.json",
    "solana/sign_tx.compute_budget_program.json",
)
def test_solana_sign_tx(client: Client, parameters, result):
    client.init_device(new_session=True)

    serialized_tx = MESSAGE.build(
        replace_account_placeholders(parameters["construct"]),
        instruction_id_formats=INSTRUCTION_ID_FORMATS,
    )

    actual_result = sign_tx(
        client,
        address_n=parse_path(parameters["address"]),
        serialized_tx=serialized_tx,
    )

    assert actual_result.signature == bytes.fromhex(result["expected_signature"])
