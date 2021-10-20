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
    "cardano/sign_tx.multisig.json",
    "cardano/sign_tx.slip39.json",
)
def test_cardano_sign_tx(client, parameters, result):
    client.init_device(new_session=True, derive_cardano=True)

    signing_mode = messages.CardanoTxSigningMode.__members__[parameters["signing_mode"]]
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])
    mint = cardano.parse_mint(parameters["mint"])
    additional_witness_requests = [
        cardano.parse_additional_witness_request(p)
        for p in parameters["additional_witness_requests"]
    ]

    if parameters.get("security_checks") == "prompt":
        device.apply_settings(
            client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
        )
    else:
        device.apply_settings(client, safety_checks=messages.SafetyCheckLevel.Strict)

    with client:
        response = cardano.sign_tx(
            client=client,
            signing_mode=signing_mode,
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
            mint=mint,
            additional_witness_requests=additional_witness_requests,
        )
        assert response == _transform_expected_result(result)


@parametrize_using_common_fixtures(
    "cardano/sign_tx.failed.json",
    "cardano/sign_tx.multisig.failed.json",
    "cardano/sign_tx_stake_pool_registration.failed.json",
)
def test_cardano_sign_tx_failed(client, parameters, result):
    client.init_device(new_session=True, derive_cardano=True)

    signing_mode = messages.CardanoTxSigningMode.__members__[parameters["signing_mode"]]
    inputs = [cardano.parse_input(i) for i in parameters["inputs"]]
    outputs = [cardano.parse_output(o) for o in parameters["outputs"]]
    certificates = [cardano.parse_certificate(c) for c in parameters["certificates"]]
    withdrawals = [cardano.parse_withdrawal(w) for w in parameters["withdrawals"]]
    auxiliary_data = cardano.parse_auxiliary_data(parameters["auxiliary_data"])
    mint = cardano.parse_mint(parameters["mint"])
    additional_witness_requests = [
        cardano.parse_additional_witness_request(p)
        for p in parameters["additional_witness_requests"]
    ]

    if parameters.get("security_checks") == "prompt":
        device.apply_settings(
            client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
        )
    else:
        device.apply_settings(client, safety_checks=messages.SafetyCheckLevel.Strict)

    with client:
        with pytest.raises(TrezorFailure, match=result["error_message"]):
            cardano.sign_tx(
                client=client,
                signing_mode=signing_mode,
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
                mint=mint,
                additional_witness_requests=additional_witness_requests,
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
                "chain_code": bytes.fromhex(witness["chain_code"])
                if witness["chain_code"]
                else None,
            }
            for witness in result["witnesses"]
        ],
    }
    if supplement := result.get("auxiliary_data_supplement"):
        transformed_result["auxiliary_data_supplement"] = {
            "type": supplement["type"],
            "auxiliary_data_hash": bytes.fromhex(supplement["auxiliary_data_hash"]),
        }
        if catalyst_signature := supplement.get("catalyst_signature"):
            transformed_result["auxiliary_data_supplement"][
                "catalyst_signature"
            ] = bytes.fromhex(catalyst_signature)
    return transformed_result
