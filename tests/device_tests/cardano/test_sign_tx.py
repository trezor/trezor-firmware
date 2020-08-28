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

from trezorlib import cardano, messages
from trezorlib.exceptions import TrezorFailure

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]


@parametrize_using_common_fixtures(
    "cardano/sign_tx.json", "cardano/sign_tx.slip39.json"
)
def test_cardano_sign_tx(client, parameters, result):
    inputs = [cardano.create_input(i) for i in parameters["inputs"]]
    outputs = [cardano.create_output(o) for o in parameters["outputs"]]
    certificates = [cardano.create_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.create_withdrawal(w) for w in parameters["withdrawals"]]

    expected_responses = [messages.PassphraseRequest()]
    expected_responses += [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other)
        for i in range(len(parameters["input_flow"]))
    ]
    expected_responses.append(messages.CardanoSignedTx())

    def input_flow():
        for sequence in parameters["input_flow"]:
            yield
            for action in sequence:
                if action == "SWIPE":
                    client.debug.swipe_up()
                elif action == "YES":
                    client.debug.press_yes()
                else:
                    raise ValueError("Invalid input action")

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client=client,
            inputs=inputs,
            outputs=outputs,
            fee=parameters["fee"],
            ttl=parameters["ttl"],
            certificates=certificates,
            withdrawals=withdrawals,
            metadata=bytes.fromhex(parameters["metadata"]),
            protocol_magic=parameters["protocol_magic"],
            network_id=parameters["network_id"],
        )
        assert response.tx_hash.hex() == result["tx_hash"]
        assert response.serialized_tx.hex() == result["serialized_tx"]


@parametrize_using_common_fixtures("cardano/sign_tx.failed.json")
def test_cardano_sign_tx_failed(client, parameters, result):
    inputs = [cardano.create_input(i) for i in parameters["inputs"]]
    outputs = [cardano.create_output(o) for o in parameters["outputs"]]
    certificates = [cardano.create_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.create_withdrawal(w) for w in parameters["withdrawals"]]

    expected_responses = [messages.PassphraseRequest(), messages.Failure()]

    with client:
        client.set_expected_responses(expected_responses)

        with pytest.raises(TrezorFailure, match=result["error_message"]):
            cardano.sign_tx(
                client=client,
                inputs=inputs,
                outputs=outputs,
                fee=parameters["fee"],
                ttl=parameters["ttl"],
                certificates=certificates,
                withdrawals=withdrawals,
                metadata=bytes.fromhex(parameters["metadata"]),
                protocol_magic=parameters["protocol_magic"],
                network_id=parameters["network_id"],
            )
