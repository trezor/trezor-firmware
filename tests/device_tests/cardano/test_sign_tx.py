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
    ["cardano/sign_tx.json", "cardano/sign_tx.slip39.json"]
)
def test_cardano_sign_tx(client, parameters, result):
    inputs = [cardano.create_input(i) for i in parameters["inputs"]]
    outputs = [cardano.create_output(o) for o in parameters["outputs"]]

    expected_responses = []
    # TODO: or we could pass the fixture json name or description/name
    if client.features.passphrase_protection:
        expected_responses += [messages.PassphraseRequest()]

    expected_responses += [
        messages.CardanoTxRequest(tx_index=i) for i in range(len(parameters["prev_tx"]))
    ]
    if result["success"]:
        expected_responses += [
            messages.ButtonRequest(code=messages.ButtonRequestType.Other),
            messages.ButtonRequest(code=messages.ButtonRequestType.Other),
            messages.CardanoSignedTx(),
        ]
    else:
        expected_responses += [messages.Failure()]

    def input_flow():
        yield
        client.debug.swipe_up()
        client.debug.press_yes()
        yield
        client.debug.swipe_up()
        client.debug.press_yes()

    with client:
        client.set_expected_responses(expected_responses)
        if result["success"]:
            client.set_input_flow(input_flow)
            response = cardano.sign_tx(
                client,
                inputs,
                outputs,
                parameters["prev_tx"],
                parameters["protocol_magic"],
            )
            assert response.tx_hash.hex() == result["tx_hash"]
            assert response.tx_body.hex() == result["tx_body"]
        else:
            with pytest.raises(TrezorFailure, match=result["error"]):
                cardano.sign_tx(
                    client,
                    inputs,
                    outputs,
                    parameters["prev_tx"],
                    parameters["protocol_magic"],
                )
