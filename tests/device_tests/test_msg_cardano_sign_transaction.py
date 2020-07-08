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
from trezorlib.cardano import NETWORK_IDS, PROTOCOL_MAGICS
from trezorlib.exceptions import TrezorFailure


class InputAction:
    """
    Test cases don't use the same input flows. These constants are used to define
    the expected input flows for each test case. Corresponding input actions
    are then executed on the device to simulate user inputs.
    """

    SWIPE = 0
    YES = 1


SAMPLE_INPUTS = {
    "byron_input": {
        "path": "m/44'/1815'/0'/0/1",
        "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
        "prev_index": 0,
    },
    "shelley_input": {
        "path": "m/1852'/1815'/0'/0/0",
        "prev_hash": "3b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7",
        "prev_index": 0,
    },
}

SAMPLE_OUTPUTS = {
    "simple_byron_output": {
        "address": "82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c2561",
        "amount": "3003112",
    },
    "byron_change_output": {
        "addressType": 8,
        "path": "m/44'/1815'/0'/0/1",
        "amount": "1000000",
    },
    "simple_shelley_output": {
        "address": "017cb05fce110fb999f01abb4f62bc455e217d4a51fde909fa9aea545443ac53c046cf6a42095e3c60310fa802771d0672f8fe2d1861138b09da61d425f3461114",
        "amount": "1",
    },
    "base_address_change_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "stakingKeyPath": "m/1852'/1815'/0'/2/0",
        "amount": "7120787",
    },
    "staking_key_hash_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "stakingKeyHash": "32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc",
        "amount": "7120787",
    },
    "pointer_address_output": {
        "addressType": 4,
        "path": "m/1852'/1815'/0'/0/0",
        "blockIndex": 1,
        "txIndex": 2,
        "certificateIndex": 3,
        "amount": "7120787",
    },
    "enterprise_address_output": {
        "addressType": 6,
        "path": "m/1852'/1815'/0'/0/0",
        "amount": "7120787",
    },
    "invalid_address": {
        "address": "83d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c256100",
        "amount": "3003112",
    },
    "invalid_cbor": {
        "address": "8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c2561158282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c2561",
        "amount": "3003112",
    },
    "invalid_crc": {
        "address": "82d818582183581c578e965bd8e000b67ae6847de0c098b5c63470dc1a51222829c482bfa0001a00000000",
        "amount": "3003112",
    },
    "large_simple_byron_output": {
        "address": "82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c2561",
        "amount": "449999999199999999",
    },
    "testnet_output": {
        "address": "82d818582583581cc817d85b524e3d073795819a25cdbb84cff6aa2bbb3a081980d248cba10242182a001a0fb6fc61",
        "amount": "3003112",
    },
    "shelley_testnet_output": {
        "address": "60a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa4",
        "amount": "1",
    },
}

VALID_VECTORS = [
    # Mainnet transaction without change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # input flow
        [[InputAction.SWIPE, InputAction.YES], [InputAction.SWIPE, InputAction.YES]],
        # tx hash
        "73e09bdebf98a9e0f17f86a2d11e0f14f4f8dae77cdf26ff1678e821f20c8db6",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018182582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e802182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840da07ac5246e3f20ebd1276476a4ae34a019dd4b264ffc22eea3c28cb0f1a6bb1c7764adeecf56bcb0bc6196fd1dbe080f3a7ef5b49f56980fe5b2881a4fdfa00582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # Mainnet transaction with change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"], SAMPLE_OUTPUTS["byron_change_output"]],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "81b14b7e62972127eb33c0b1198de6430540ad3a98eec621a3194f2baac43a43",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e882582b82d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840d909b16038c4fd772a177038242e6793be39c735430b03ee924ed18026bd28d06920b5846247945f1204276e4b759aa5ac05a4a73b49ce705ab0e5e54a3a170e582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # simple transaction with base address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["base_address_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [[InputAction.SWIPE, InputAction.YES], [InputAction.SWIPE, InputAction.YES]],
        # tx hash
        "1652fbf24d30316977f8ac117bfdf83054affb9baebfeb1f46b4ab5b8ee878fe",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7000182825841017cb05fce110fb999f01abb4f62bc455e217d4a51fde909fa9aea545443ac53c046cf6a42095e3c60310fa802771d0672f8fe2d1861138b09da61d425f3461114018258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c158408bc12e9a888a848ca79a9e52749fd429f36d02c6728c61672cf851562f616ac3b1070533a30395709da64bf323d4e70a42d71828386bfae7db07fc3d010e3e0df6",
    ),
    # simple transaction with base address change output with staking key hash
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["staking_key_hash_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "f20ad1550ec356f871a858a8946dc86bdf982ff09f280beae781ab7c634baf88",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7000182825841017cb05fce110fb999f01abb4f62bc455e217d4a51fde909fa9aea545443ac53c046cf6a42095e3c60310fa802771d0672f8fe2d1861138b09da61d425f3461114018258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc1a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c15840fb999e6919fb2991f7751b06a6e8b3c65693023ef692068d98277a1108395714ed7e1e2040bd5d7e45e6679b89fead43c3401defa9d79560b6722cd2574b220af6",
    ),
    # simple transaction with pointer address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["pointer_address_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "3d1b607a22004e79db08179568497ed10263992472d3e402fbd0d0907679c385",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7000182825841017cb05fce110fb999f01abb4f62bc455e217d4a51fde909fa9aea545443ac53c046cf6a42095e3c60310fa802771d0672f8fe2d1861138b09da61d425f3461114018258204180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa0102031a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c158405ce3bc8c68dae9a320edf7bf08f3cd4f77adf2c0cd634c2b9ffa365b72de6b33f21afce8a8dc448644a12156fa0a71625bf4c9b02b4b98b56fcc3f06e42b0d0bf6",
    ),
    # simple transaction with enterprise address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["enterprise_address_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "ecc43fed0c00a140a36a517cf0982994103776d68a29ca23b48d902b2222706b",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7000182825841017cb05fce110fb999f01abb4f62bc455e217d4a51fde909fa9aea545443ac53c046cf6a42095e3c60310fa802771d0672f8fe2d1861138b09da61d425f34611140182581d6180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa1a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c158406b72a593d657e80ac2971d5cdc443c138e29adbe8400e62facc5634df6bfad29bac220bd080082b67e7283eed99d33ce564762fe35734adaa444d555adf38701f6",
    ),
    # Testnet transaction
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["testnet_output"],
            SAMPLE_OUTPUTS["shelley_testnet_output"],
            SAMPLE_OUTPUTS["byron_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "8bbe6dd4185cf8b0fe6ede75f707d1e367589d33ff321d4f2646ebe800df43d6",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018382582f82d818582583581cc817d85b524e3d073795819a25cdbb84cff6aa2bbb3a081980d248cba10242182a001a0fb6fc611a002dd2e882582160a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa40182582f82d818582583581c98c3a558f39d1d993cc8770e8825c70a6d0f5a9eb243501c4526c29da10242182a001aa8566c011a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840ad6cdb5106db5c295095c389808189d58ace73577aedfe670fbf9cb51c228c3ee55d98ba7896599beebedb64f01798ef00ffb32c7ed13732cad9ad6817237709582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63545a10242182af6",
    ),
]

INVALID_VECTORS = [
    # Output address is a valid CBOR but invalid Cardano address
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_address"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address is invalid CBOR
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_cbor"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address has invalid CRC
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_crc"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Fee is too high
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        45000000000000001,
        # ttl
        10,
        # error message
        "Fee is out of range!",
    ),
    # Output total is too high
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["large_simple_byron_output"],
            SAMPLE_OUTPUTS["byron_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # error message
        "Total transaction amount is out of range!",
    ),
    # Mainnet transaction with testnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["testnet_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Testnet transaction with mainnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Shelley mainnet transaction with testnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["shelley_testnet_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Shelley testnet transaction with mainnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_shelley_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Testnet protocol magic with mainnet network id
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_shelley_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid network id/protocol magic combination!",
    ),
    # Mainnet protocol magic with testnet network id
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid network id/protocol magic combination!",
    ),
]


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,network_id,inputs,outputs,fee,ttl,input_flow_sequences,tx_hash,serialized_tx",
    VALID_VECTORS,
)
def test_cardano_sign_tx(
    client,
    protocol_magic,
    network_id,
    inputs,
    outputs,
    fee,
    ttl,
    input_flow_sequences,
    tx_hash,
    serialized_tx,
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other)
        for i in range(len(input_flow_sequences))
    ]
    expected_responses.append(messages.CardanoSignedTx())

    def input_flow():
        for sequence in input_flow_sequences:
            yield
            for action in sequence:
                if action == InputAction.SWIPE:
                    client.debug.swipe_up()
                elif action == InputAction.YES:
                    client.debug.press_yes()
                else:
                    raise ValueError("Invalid input action")

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client, inputs, outputs, fee, ttl, protocol_magic, network_id
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.serialized_tx.hex() == serialized_tx


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,network_id,inputs,outputs,fee,ttl,expected_error_message",
    INVALID_VECTORS,
)
def test_cardano_sign_tx_validation(
    client,
    protocol_magic,
    network_id,
    inputs,
    outputs,
    fee,
    ttl,
    expected_error_message,
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [messages.Failure()]

    with client:
        client.set_expected_responses(expected_responses)

        with pytest.raises(TrezorFailure, match=expected_error_message):
            cardano.sign_tx(
                client, inputs, outputs, fee, ttl, protocol_magic, network_id
            )
