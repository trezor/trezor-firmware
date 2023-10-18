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
from .construct.instructions import INSTRUCTION_ID_FORMATS, Instruction
from .construct.transaction import Message

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.solana,
    pytest.mark.skip_t1,
]


# TODO: remove at the end of review process
@parametrize_using_common_fixtures(
    "solana/sign_tx.tmp.json",
)
def test_solana_tx_tmp(client: Client, parameters, result):
    client.init_device(new_session=True)

    serialized_tx = parameters["tx"]

    actual_result = sign_tx(
        client,
        address_n=parse_path("m/44'/501'/0'/0'"),
        serialized_tx=bytes.fromhex(serialized_tx),
    )

    assert actual_result.signature == bytes.fromhex(result["signature"])


@parametrize_using_common_fixtures(
    "solana/sign_tx.system_program.json",
    "solana/sign_tx.stake_program.json",
    "solana/sign_tx.associated_token_account_program.json",
    "solana/sign_tx.memo_program.json",
    "solana/sign_tx.compute_budget_program.json",
    "solana/sign_tx.token_program.json",
    "solana/sign_tx.unknown_instructions.json",
)
def test_solana_sign_tx(client: Client, parameters, result):
    client.init_device(new_session=True)

    serialized_tx = _serialize_tx(parameters["construct"])

    actual_result = sign_tx(
        client,
        address_n=parse_path(parameters["address"]),
        serialized_tx=serialized_tx,
    )

    assert actual_result.signature == bytes.fromhex(result["expected_signature"])


def _serialize_tx(tx_construct):
    serialized_instructions = [
        Instruction.build(
            instruction,
            program_id=tx_construct["accounts"][instruction["program_index"]],
            instruction_id=instruction["data"]["instruction_id"]
            if "instruction_id" in instruction["data"]
            else -1,
            instruction_id_formats=INSTRUCTION_ID_FORMATS,
        )
        for instruction in tx_construct["instructions"]
    ]

    message_construct = {
        "version": tx_construct["version"],
        "header": tx_construct["header"],
        "accounts": tx_construct["accounts"],
        "blockhash": tx_construct["blockhash"],
        "instructions": serialized_instructions,
        "luts": tx_construct["luts"],
    }

    return Message.build(
        message_construct,
    )
