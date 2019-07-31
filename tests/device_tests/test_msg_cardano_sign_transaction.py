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

from .conftest import setup_client

PROTOCOL_MAGICS = {"mainnet": 764824073, "testnet": 1097911063}

SAMPLE_INPUTS = [
    {
        "input": {
            "path": "m/44'/1815'/0'/0/1",
            "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
            "prev_index": 0,
            "type": 0,
        },
        "prev_tx": "839f8200d818582482582008abb575fac4c39d5bf80683f7f0c37e48f4e3d96e37d1f6611919a7241b456600ff9f8282d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a00305becffa0",
    }
]

VALID_VECTORS = [
    # Mainnet transaction without change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUTS[0]["input"]],
        # outputs
        [
            {
                "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
                "amount": "3003112",
            }
        ],
        # transactions
        [SAMPLE_INPUTS[0]["prev_tx"]],
        # tx hash
        "799c65e8a2c0b1dc4232611728c09d3f3eb0d811c077f8e9798f84605ef1b23d",
        # tx body
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a6355840312c01c27317415b0b8acc86aa789da877fe7e15c65b7ea4c4565d8739117f5f6d9d38bf5d058f7be809b2b9b06c1d79fc6b20f9a4d76d8c89bae333edf5680c",
    ),
    # Mainnet transaction with change
    (
        # protocol magic (mainnet)
        764824073,
        # inputs
        [
            {
                "path": "m/44'/1815'/0'/0/1",
                "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
                "prev_index": 0,
                "type": 0,
            }
        ],
        # outputs
        [
            {
                "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
                "amount": "3003112",
            },
            {"path": "m/44'/1815'/0'/0/1", "amount": "1000000"},
        ],
        # transactions
        [SAMPLE_INPUTS[0]["prev_tx"]],
        # tx hash
        "40bf94518f31aba7779dd99aa71fe867887bcb3e0bac2c6dc33d3f20ec74a6b1",
        # tx body
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e88282d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a000f4240ffa0818200d818588582584089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63558400b47193163462023bdb72f03b2f6afc8e3645dbc9252cb70f7516da402ce3b8468e4a60929674de5862d6253315008e07b60aa189f5c455dd272ff1c84c89d0c",
    ),
    # Testnet transaction
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # inputs
        [SAMPLE_INPUTS[0]["input"]],
        # outputs
        [
            {
                "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
                "amount": "3003112",
            }
        ],
        # transactions
        [SAMPLE_INPUTS[0]["prev_tx"]],
        # tx hash
        "799c65e8a2c0b1dc4232611728c09d3f3eb0d811c077f8e9798f84605ef1b23d",
        # tx body
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63558403594ee7e2bfe4c84f886a8336cecb7c42983ce9a057345ebb6294a436087d8db93ca78cf514c7c48edff4c8435f690a5817951e2b55d2db729875ee7cc0f7d08",
    ),
]

INVALID_VECTORS = [
    # Output address is a valid CBOR but invalid Cardano address
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUTS[0]["input"]],
        # outputs
        [
            {
                "address": "jsK75PTH2esX8k4Wvxenyz83LJJWToBbVmGrWUer2CHFHanLseh7r3sW5X5q",
                "amount": "3003112",
            }
        ],
        # transactions
        [SAMPLE_INPUTS[0]["prev_tx"]],
        "Invalid output address!",
    ),
    # Output address is an invalid CBOR
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUTS[0]["input"]],
        # outputs
        [
            {
                "address": "jsK75PTH2esX8k4Wvxenyz83LJJWToBbVmGrWUer2CHFHanLseh7r3sW5X5q",
                "amount": "3003112",
            }
        ],
        # transactions
        [
            "839f8200d818582482582008abb575fac4c39d5bf80683f7f0c37e48f4e3d96e37d1f6611919a7241b456600ff9f8282d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a00305becffa0"
        ],
        "Invalid output address!",
    ),
    # Output address is invalid CBOR
    (
        # protocol magic (mainnet)
        764824073,
        # inputs
        [
            {
                "path": "m/44'/1815'/0'/0/1",
                "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
                "prev_index": 0,
                "type": 0,
            }
        ],
        # outputs
        [
            {
                "address": "5dnY6xgRcNUSLGa4gfqef2jGAMHb7koQs9EXErXLNC1LiMPUnhn8joXhvEJpWQtN3F4ysATcBvCn5tABgL3e4hPWapPHmcK5GJMSEaET5JafgAGwSrznzL1Mqa",
                "amount": "3003112",
            }
        ],
        # transactions
        [SAMPLE_INPUTS[0]["prev_tx"]],
        "Invalid output address!",
    ),
]


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@setup_client()
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,transactions,tx_hash,tx_body", VALID_VECTORS
)
def test_cardano_sign_tx(
    client, protocol_magic, inputs, outputs, transactions, tx_hash, tx_body
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [
        messages.CardanoTxRequest(tx_index=i) for i in range(len(transactions))
    ]
    expected_responses += [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.CardanoSignedTx(),
    ]

    def input_flow():
        yield
        client.debug.swipe_down()
        client.debug.press_yes()
        yield
        client.debug.swipe_down()
        client.debug.press_yes()

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client, inputs, outputs, transactions, protocol_magic
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.tx_body.hex() == tx_body


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@setup_client()
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,transactions,expected_error_message", INVALID_VECTORS
)
def test_cardano_sign_tx_validation(
    client, protocol_magic, inputs, outputs, transactions, expected_error_message
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [
        messages.CardanoTxRequest(tx_index=i) for i in range(len(transactions))
    ]
    expected_responses += [messages.Failure()]

    with client:
        client.set_expected_responses(expected_responses)

        with pytest.raises(TrezorFailure) as exc:
            cardano.sign_tx(client, inputs, outputs, transactions, protocol_magic)

        assert exc.value.args[1] == expected_error_message
