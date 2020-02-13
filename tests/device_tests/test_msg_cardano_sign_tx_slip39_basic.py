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

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6

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
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b584032a773bcd60c83880de09676c45e52cc2c2189c1b46d93de596a5cf6e3e93041c22e6e5762144feb65b40e905659c9b5e51528fa6574273279c2507a2b996f0e",
    ),
    # Mainnet transaction with change
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
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
        "5a3921053daabc6a2ffc1528963352fa8ea842bd04056371effcd58256e0cd55",
        # tx body
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e88282d818582183581c2ea63b3db3a1865f59c11762a5aede800ed8f2dc0605d75df2ed7c9ca0001ae82668161a000f4240ffa0818200d818588582584024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b5840ea38a37167d652fd35ac3517a6b3a5ec73e01a9f3b6d57d645c7727856a17a2c8d9403b497e148811cb087822c49b5ab6e14b1bc78acc21eca434c3e5147260f",
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
        "82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b58407aab2a707a6d295c0a93e396429721c48d2c09238e32112f2e1d14a8296ff463204240e7d9168e2dfe8276f426cd1f73f1254df434cdab7c942e2a920c8ce800",
    ),
]


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,transactions,tx_hash,tx_body", VALID_VECTORS
)
def test_cardano_sign_tx(
    client, protocol_magic, inputs, outputs, transactions, tx_hash, tx_body
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [messages.PassphraseRequest()]
    expected_responses += [
        messages.CardanoTxRequest(tx_index=i) for i in range(len(transactions))
    ]
    expected_responses += [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.CardanoSignedTx(),
    ]

    def input_flow():
        yield
        client.debug.swipe_up()
        client.debug.press_yes()
        yield
        client.debug.swipe_up()
        client.debug.press_yes()

    client.use_passphrase("TREZOR")
    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client, inputs, outputs, transactions, protocol_magic
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.tx_body.hex() == tx_body
