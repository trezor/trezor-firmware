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

from trezorlib import btc, cardano, device, messages, misc
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings
from ..payment_req import (
    CoinPurchaseMemo,
    RefundMemo,
    TextDetailsMemo,
    make_payment_request,
)

pytestmark = [pytest.mark.altcoin, pytest.mark.cardano, pytest.mark.models("core")]


def show_details_input_flow(client: Client):
    yield
    client.debug.read_layout()
    if client.layout_type is LayoutType.Bolt:
        SHOW_ALL_BUTTON_POSITION = (143, 167)
        client.debug.click(SHOW_ALL_BUTTON_POSITION)
    elif client.layout_type is LayoutType.Caesar:
        # Caesar - right button for "Show all"
        client.debug.press_yes()
    elif client.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
        # Delizia - "Show all" button from context menu
        client.debug.click(client.debug.screen_buttons.menu())
        client.debug.click(client.debug.screen_buttons.vertical_menu_items()[0])
    else:
        raise NotImplementedError
    # reset ui flow to continue "automatically"
    client.ui.reset_input_flow()
    yield


@parametrize_using_common_fixtures(
    "cardano/sign_tx_stake_pool_registration.json",
    "cardano/sign_tx.json",
    "cardano/sign_tx.multisig.json",
    "cardano/sign_tx.plutus.json",
    "cardano/sign_tx.slip39.json",
)
def test_cardano_sign_tx(session: Session, parameters, result):
    response = call_sign_tx(
        session,
        parameters,
        input_flow=lambda client: InputFlowConfirmAllWarnings(session.client).get(),
    )
    assert response == _transform_expected_result(result)


@parametrize_using_common_fixtures("cardano/sign_tx.show_details.json")
def test_cardano_sign_tx_show_details(session: Session, parameters, result):
    response = call_sign_tx(session, parameters, show_details_input_flow, chunkify=True)
    assert response == _transform_expected_result(result)


@parametrize_using_common_fixtures(
    "cardano/sign_tx_stake_pool_registration.failed.json",
    "cardano/sign_tx.failed.json",
    "cardano/sign_tx.multisig.failed.json",
    "cardano/sign_tx.plutus.failed.json",
)
def test_cardano_sign_tx_failed(session: Session, parameters, result):
    with pytest.raises(TrezorFailure, match=result["error_message"]):
        call_sign_tx(session, parameters, None)


def call_sign_tx(session: Session, parameters, input_flow=None, chunkify: bool = False):
    # session.init_device(new_session=True, derive_cardano=True)

    signing_mode = messages.CardanoTxSigningMode.__members__[parameters["signing_mode"]]
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])
    mint = cardano.parse_mint(parameters["mint"])
    script_data_hash = cardano.parse_script_data_hash(parameters["script_data_hash"])
    collateral_inputs = [
        cardano.parse_collateral_input(i) for i in parameters["collateral_inputs"]
    ]
    required_signers = [
        cardano.parse_required_signer(s) for s in parameters["required_signers"]
    ]
    collateral_return = (
        cardano.parse_output(parameters["collateral_return"])
        if parameters["collateral_return"] is not None
        else None
    )
    reference_inputs = [
        cardano.parse_reference_input(i) for i in parameters["reference_inputs"]
    ]
    additional_witness_requests = [
        cardano.parse_additional_witness_request(p)
        for p in parameters["additional_witness_requests"]
    ]

    if parameters.get("security_checks") == "prompt":
        device.apply_settings(
            session, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
        )
    else:
        device.apply_settings(session, safety_checks=messages.SafetyCheckLevel.Strict)

    if parameters.get("payment_req"):
        # Note: "payment_req" in the JSON is just a boolean,
        # which makes us generate a payment request here.
        # It could be changed to encode the payment request in the JSON,
        # but it feels overkill for now.
        purchase_memo = CoinPurchaseMemo(
            amount="0.00001 BTC",
            coin_name="Bitcoin",
            slip44=0,
            address_n=parse_path("m/44h/0h/0h/0/0"),
        )
        purchase_memo.address_resp = btc.get_authenticated_address(
            session, purchase_memo.coin_name, purchase_memo.address_n
        )
        refund_memo = RefundMemo(address_n=parse_path("m/44h/1815h/0h/0/2"))
        refund_memo.address_resp = cardano.get_authenticated_address(
            session, cardano.create_address_parameters(8, refund_memo.address_n)
        )
        text_details_memo = TextDetailsMemo(
            title="Are you sure...",
            text="... you want to swap your valuable ADA for some sats?",
        )
        memos = [purchase_memo, refund_memo, text_details_memo]
        nonce = misc.get_nonce(session)
        payment_request = make_payment_request(
            session,
            recipient_name="trezor.io",
            slip44=1815,
            outputs=[(o[0].amount, o[0].address) for o in outputs],
            memos=memos,
            nonce=nonce,
        )
    else:
        payment_request = None

    with session.client as client:
        if input_flow is not None:
            session.client.watch_layout()
            client.set_input_flow(input_flow(session.client))

        return cardano.sign_tx(
            session=session,
            signing_mode=signing_mode,
            inputs=inputs,
            outputs=outputs,
            fee=parameters["fee"],
            ttl=parameters["ttl"],
            validity_interval_start=parameters["validity_interval_start"],
            certificates=certificates,
            withdrawals=withdrawals,
            protocol_magic=parameters["protocol_magic"],
            network_id=parameters["network_id"],
            auxiliary_data=auxiliary_data,
            mint=mint,
            script_data_hash=script_data_hash,
            collateral_inputs=collateral_inputs,
            required_signers=required_signers,
            collateral_return=collateral_return,
            total_collateral=parameters["total_collateral"],
            reference_inputs=reference_inputs,
            additional_witness_requests=additional_witness_requests,
            include_network_id=parameters["include_network_id"],
            chunkify=chunkify,
            tag_cbor_sets=parameters["tag_cbor_sets"],
            payment_req=payment_request,
        )


def _transform_expected_result(result):
    """Transform the JSON representation of the expected result into the format which is returned by trezorlib.

    This involves converting the hex strings into real binary values."""
    transformed_result = {
        "tx_hash": bytes.fromhex(result["tx_hash"]),
        "witnesses": [
            {
                "type": witness["type"],
                "pub_key": bytes.fromhex(witness["pub_key"]),
                "signature": bytes.fromhex(witness["signature"]),
                "chain_code": (
                    bytes.fromhex(witness["chain_code"])
                    if witness["chain_code"]
                    else None
                ),
            }
            for witness in result["witnesses"]
        ],
    }
    if supplement := result.get("auxiliary_data_supplement"):
        transformed_result["auxiliary_data_supplement"] = {
            "type": supplement["type"],
            "auxiliary_data_hash": bytes.fromhex(supplement["auxiliary_data_hash"]),
        }
        if cvote_registration_signature := supplement.get(
            "cvote_registration_signature"
        ):
            transformed_result["auxiliary_data_supplement"][
                "cvote_registration_signature"
            ] = bytes.fromhex(cvote_registration_signature)
    return transformed_result


@pytest.mark.models(
    "core",
    skip="t2t1",
    reason="T1 does not support payment requests. Payment requests not yet implemented on model T.",
)
@pytest.mark.altcoin
@pytest.mark.experimental
@parametrize_using_common_fixtures(
    "cardano/sign_tx.slip24.json",
)
def test_signtx_payment_req(session: Session, parameters, result):
    call_sign_tx(session, parameters, None)


@pytest.mark.models(
    "core",
    skip="t2t1",
    reason="T1 does not support payment requests. Payment requests not yet implemented on model T.",
)
@pytest.mark.altcoin
@pytest.mark.experimental
@parametrize_using_common_fixtures(
    "cardano/sign_tx.slip24.failed.json",
)
def test_sign_tx_payment_req_failed(session: Session, parameters, result):
    with pytest.raises(TrezorFailure, match=result["error_message"]):
        call_sign_tx(session, parameters, None)
