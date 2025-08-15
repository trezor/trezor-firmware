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

from trezorlib import btc, messages, misc
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.solana import get_authenticated_address, sign_tx
from trezorlib.tools import b58decode, parse_path

from ...common import parametrize_using_common_fixtures
from ...definitions import encode_solana_token
from ...input_flows import InputFlowConfirmAllWarnings
from ..payment_req import (
    CoinPurchaseMemo,
    RefundMemo,
    TextDetailsMemo,
    make_payment_request,
)
from .construct.instructions import PROGRAMS, UnknownInstruction
from .construct.transaction import Message, RawInstruction

pytestmark = [pytest.mark.altcoin, pytest.mark.solana, pytest.mark.models("core")]


@parametrize_using_common_fixtures(
    "solana/sign_tx.system_program.json",
    "solana/sign_tx.stake_program.json",
    "solana/sign_tx.associated_token_account_program.json",
    "solana/sign_tx.memo_program.json",
    "solana/sign_tx.compute_budget_program.json",
    "solana/sign_tx.token_program.json",
    "solana/sign_tx.unknown_instructions.json",
    "solana/sign_tx.predefined_transactions.json",
    "solana/sign_tx.staking_transactions.json",
    "solana/sign_tx.payment_request.json",
)
def test_solana_sign_tx(session: Session, parameters, result):
    serialized_tx = _serialize_tx(parameters["construct"])

    with session.client as client:
        IF = InputFlowConfirmAllWarnings(session.client)
        client.set_input_flow(IF.get())
        additional_info = None
        if "additional_info" in parameters:
            token = parameters["additional_info"].get("token")
            if token:
                encoded_token = encode_solana_token(
                    symbol=token["symbol"],
                    mint=b58decode(token["mint"]),
                    name=token["name"],
                )
            else:
                encoded_token = None
            additional_info = messages.SolanaTxAdditionalInfo(
                token_accounts_infos=[
                    messages.SolanaTxTokenAccountInfo(
                        base_address=token_account["base_address"],
                        token_program=token_account["token_program"],
                        token_mint=token_account["token_mint"],
                        token_account=token_account["token_account"],
                    )
                    for token_account in parameters["additional_info"].get(
                        "token_accounts_infos", []
                    )
                ],
                encoded_token=encoded_token,
            )

        if parameters.get("payment_req"):
            purchase_memo = CoinPurchaseMemo(
                amount="0.00001 BTC",
                coin_name="Bitcoin",
                slip44=0,
                address_n=parse_path("m/44h/0h/0h/0/0"),
            )
            purchase_memo.address_resp = btc.get_authenticated_address(
                session, purchase_memo.coin_name, purchase_memo.address_n
            )
            refund_memo = RefundMemo(address_n=parse_path("m/44h/501h/0h/1h"))
            refund_memo.address_resp = get_authenticated_address(
                session, refund_memo.address_n, False
            )
            text_details_memo = TextDetailsMemo(
                title="Are you sure...",
                text="... you want to swap your valuable FAKE tokens for some sats?",
            )
            memos = [purchase_memo, refund_memo, text_details_memo]
            nonce = misc.get_nonce(session)
            payment_request = make_payment_request(
                session,
                recipient_name="trezor.io",
                slip44=501,
                outputs=[
                    (
                        i["data"]["amount"],
                        parameters["construct"]["accounts"][
                            i["accounts"]["destination_account"]
                        ],
                    )
                    for i in parameters["construct"]["instructions"]
                ],
                memos=memos,
                nonce=nonce,
            )
        else:
            payment_request = None

        if "expected_signature" in result:
            actual_result = sign_tx(
                session,
                address_n=parse_path(parameters["address"]),
                serialized_tx=serialized_tx,
                additional_info=additional_info,
                payment_req=payment_request,
            )

            assert actual_result == bytes.fromhex(result["expected_signature"])
        elif "error_message" in result:
            with pytest.raises(TrezorFailure, match=result["error_message"]):
                sign_tx(
                    session,
                    address_n=parse_path(parameters["address"]),
                    serialized_tx=serialized_tx,
                    additional_info=additional_info,
                    payment_req=payment_request,
                )
        else:
            assert False, "Invalid expected result"


def _serialize_tx(tx_construct):
    serialized_instructions = []
    for instruction in tx_construct["instructions"]:
        program = tx_construct["accounts"][instruction["program_index"]]
        builder = PROGRAMS.get(program, UnknownInstruction)
        serialized_instruction = builder.build(instruction)
        raw_instruction = RawInstruction.parse(serialized_instruction)
        serialized_instructions.append(raw_instruction)

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
