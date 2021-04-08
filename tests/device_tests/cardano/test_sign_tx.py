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

from trezorlib import cardano, device, messages
from trezorlib.exceptions import TrezorFailure

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]


@parametrize_using_common_fixtures(
    "cardano/sign_tx_stake_pool_registration.json",
    "cardano/sign_tx.json",
    "cardano/sign_tx.slip39.json",
)
def test_cardano_sign_tx(client, parameters, result):
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])

    input_flow = parameters.get("input_flow", ())

    if parameters.get("security_checks") == "prompt":
        device.apply_settings(
            client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
        )
    else:
        device.apply_settings(client, safety_checks=messages.SafetyCheckLevel.Strict)

    with client:
        client.set_input_flow(_to_device_actions(client, input_flow))

        response = cardano.sign_tx(
            client=client,
            inputs=inputs,
            outputs=outputs,
            fee=parameters["fee"],
            ttl=parameters.get("ttl"),
            validity_interval_start=parameters.get("validity_interval_start"),
            certificates=certificates,
            withdrawals=withdrawals,
            protocol_magic=parameters["protocol_magic"],
            network_id=parameters["network_id"],
            auxiliary_data=auxiliary_data,
        )
        assert response.tx_hash.hex() == result["tx_hash"]
        assert response.serialized_tx.hex() == result["serialized_tx"]


@parametrize_using_common_fixtures(
    "cardano/sign_tx.failed.json", "cardano/sign_tx_stake_pool_registration.failed.json"
)
def test_cardano_sign_tx_failed(client, parameters, result):
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])

    input_flow = parameters.get("input_flow", ())

    with client:
        client.set_input_flow(_to_device_actions(client, input_flow))

        with pytest.raises(TrezorFailure, match=result["error_message"]):
            cardano.sign_tx(
                client=client,
                inputs=inputs,
                outputs=outputs,
                fee=parameters["fee"],
                ttl=parameters.get("ttl"),
                validity_interval_start=parameters.get("validity_interval_start"),
                certificates=certificates,
                withdrawals=withdrawals,
                protocol_magic=parameters["protocol_magic"],
                network_id=parameters["network_id"],
                auxiliary_data=auxiliary_data,
            )


@parametrize_using_common_fixtures("cardano/sign_tx.chunked.json")
def test_cardano_sign_tx_with_multiple_chunks(client, parameters, result):
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])

    input_flow = parameters.get("input_flow", ())

    expected_responses = [
        messages.PassphraseRequest(),
        messages.ButtonRequest(),
        messages.ButtonRequest(),
    ]
    expected_responses += [
        messages.CardanoSignedTxChunk(signed_tx_chunk=bytes.fromhex(signed_tx_chunk))
        for signed_tx_chunk in result["signed_tx_chunks"]
    ]
    expected_responses += [
        messages.CardanoSignedTx(tx_hash=bytes.fromhex(result["tx_hash"]))
    ]

    with client:
        client.set_input_flow(_to_device_actions(client, input_flow))
        client.set_expected_responses(expected_responses)

        response = cardano.sign_tx(
            client=client,
            inputs=inputs,
            outputs=outputs,
            fee=parameters["fee"],
            ttl=parameters.get("ttl"),
            validity_interval_start=parameters.get("validity_interval_start"),
            certificates=certificates,
            withdrawals=withdrawals,
            protocol_magic=parameters["protocol_magic"],
            network_id=parameters["network_id"],
            auxiliary_data=auxiliary_data,
        )
        assert response.tx_hash.hex() == result["tx_hash"]
        assert response.serialized_tx.hex() == result["serialized_tx"]


def _to_device_actions(client, input_flow):
    if not input_flow:
        yield

    for sequence in input_flow:
        yield
        for action in sequence:
            if action == "SWIPE":
                client.debug.swipe_up()
            elif action == "YES":
                client.debug.press_yes()
            else:
                raise ValueError("Invalid input action")
