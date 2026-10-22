# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent, LayoutType
from trezorlib.exceptions import TrezorFailure
from trezorlib.solana import get_authenticated_address, sign_tx
from trezorlib.testing import translations as TR
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
from .construct.transaction import Message, RawInstruction, serialize_v1_tx

pytestmark = [pytest.mark.altcoin, pytest.mark.solana, pytest.mark.models("core")]


def get_amount_and_destination(parameters, instruction):
    if "lamports" in instruction["data"]:
        # native SOL transfer
        amount = instruction["data"]["lamports"]
        destination = instruction["accounts"]["recipient_account"]
    else:
        # token transfer
        amount = instruction["data"]["amount"]
        destination = instruction["accounts"]["destination_account"]

    return amount, parameters["construct"]["accounts"][destination]


@parametrize_using_common_fixtures(
    "solana/sign_tx.system_program.json",
    "solana/sign_tx.stake_program.json",
    "solana/sign_tx.associated_token_account_program.json",
    "solana/sign_tx.memo_program.json",
    "solana/sign_tx.compute_budget_program.json",
    "solana/sign_tx.token_program.json",
    "solana/sign_tx.token_2022_program.json",
    "solana/sign_tx.unknown_instructions.json",
    "solana/sign_tx.predefined_transactions.json",
    "solana/sign_tx.staking_transactions.json",
    "solana/sign_tx.payment_request.json",
    "solana/sign_tx.v1_transactions.json",
)
def test_solana_sign_tx(session: Session, parameters, result):
    serialized_tx = _serialize_tx(parameters["construct"])

    with session.test_ctx as client:
        IF = InputFlowConfirmAllWarnings(session)
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
                amount="0.00001 BTC",
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
                recipient_name="trezor.io",
                slip44=501,
                outputs=[
                    get_amount_and_destination(parameters, i)
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
                chunkify=parameters.get("chunkify", False),
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
                    chunkify=parameters.get("chunkify", False),
                )
        else:
            assert False, "Invalid expected result"


@pytest.mark.models("delizia", "eckhart")
@pytest.mark.parametrize("show_details", (False, True))
def test_solana_sign_tx_skip_details(session: Session, show_details: bool):
    """Skip the review from the blind signing warning, optionally return to it."""
    # an unknown instruction with two signers
    serialized_tx = _serialize_tx(
        {
            "version": None,
            "header": {"signers": 2, "readonly_signers": 0, "readonly_non_signers": 1},
            "accounts": [
                "14CCvQzQzHCVgZM3j9soPnXuJXh1RmCfwLVUcdfbZVBS",
                "AeDJ1BqA7ruBbd6mEcS1QNxFbT8FQbiBVuN9NqK94Taq",
                "AeDJ1BqA7ruBbd6mEcS1QNxFbT8FQbiBVuN9NqK94Taq",
            ],
            "blockhash": "2p4rYZAaFfV5Uk5ugdG5KPNty9Uda9B3b4gWB8qnNqak",
            "instructions": [
                {"program_index": 2, "accounts": [0, 1], "data": "04deadbeef"}
            ],
            "luts": [],
        }
    )
    debug = session.debug
    reviewed: list[LayoutContent] = []

    def select_first_menu_item(expected: str) -> None:
        debug.click(debug.screen_buttons.menu())
        assert debug.button_actions.navigate_to_menu_item(0) == expected

    def input_flow():
        assert (yield).name == "warning_blind_signing"  # blind signing warning
        assert debug.read_layout().title() == TR.solana__title_blind_signing
        select_first_menu_item(TR.solana__skip_details)

        assert (yield).name == "confirm_blind_signing"  # signing without review
        if show_details:
            select_first_menu_item(TR.buttons__show_details)
            # the review continues as usual
            yield from client.ui.default_input_flow(on_page=reviewed.append)
        else:
            if debug.layout_type is LayoutType.Eckhart:
                hold_button = debug.screen_buttons.ok()
            elif debug.layout_type is LayoutType.Delizia:
                hold_button = debug.screen_buttons.tap_to_confirm()
            else:
                raise ValueError(f"Unsupported layout type: {debug.layout_type}")
            debug.click(hold_button, hold_ms=2000)
            # ending the input flow here makes any further screen fail the test
            # ("input flow ended prematurely")

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        signature = sign_tx(
            session,
            address_n=parse_path("m/44h/501h/0h/0h"),
            serialized_tx=serialized_tx,
            additional_info=None,
        )

    if show_details:
        # the review starts with the first screen after the warning
        assert reviewed[0].title() == TR.solana__multiple_signers

    # same as the "Unknown instruction" fixture
    assert signature == bytes.fromhex(
        "90093762546ad274def9b20ca6c441564193f2c7213cac704aefc6b7d65ebb31"
        "5415fa7528728279a6688e2c99aa572d5af17b21a15a1d06b94e03df4ce53205"
    )


def _serialize_tx(tx_construct):
    serialized_instructions = []
    for instruction in tx_construct["instructions"]:
        program = tx_construct["accounts"][instruction["program_index"]]
        builder = PROGRAMS.get(program, UnknownInstruction)
        serialized_instruction = builder.build(instruction)
        raw_instruction = RawInstruction.parse(serialized_instruction)
        serialized_instructions.append(raw_instruction)

    if tx_construct["version"] == 1:
        return serialize_v1_tx(
            tx_construct["header"],
            tx_construct["accounts"],
            tx_construct["blockhash"],
            [raw_instruction.value for raw_instruction in serialized_instructions],
            tx_construct.get("config"),
        )

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
