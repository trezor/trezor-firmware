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

NETWORK_IDS = {"mainnet": 0}

SHELLEY_TEST_VECTORS_MNEMONIC = (
    "test walk nut penalty hip pave soap entry language right filter choice"
)

# input flow sequence constants
SWIPE = "SWIPE"
YES = "YES"
YIELD = "YIELD"

SAMPLE_INPUTS = {
    "simple_input": {
        "path": "m/1852'/1815'/0'/0/0",
        "prev_hash": "3b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7",
        "prev_index": 0,
        # todo: GK - type can be removed?
        "type": 0,
    },
}

SAMPLE_OUTPUTS = {
    "simple_output": {
        "address": "61a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa4",
        "amount": "1",
    },
    "simple_change_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "amount": "7120787",
    },
    "staking_key_hash_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "stakingKeyHash": "122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277",
        "amount": "7120787",
    },
    "pointer_address_output": {
        "addressType": 1,
        "path": "m/1852'/1815'/0'/0/0",
        "pointer": {"block_index": 1, "tx_index": 2, "certificate_index": 3},
        "amount": "7120787",
    },
}

SAMPLE_CERTIFICATES = {
    "stake_registration": {
        "type": "stake_registration",
        "path": "m/1852'/1815'/0'/2/0",
    },
    "stake_deregistration": {
        "type": "stake_deregistration",
        "path": "m/1852'/1815'/0'/2/0",
    },
    "stake_delegation": {
        "type": "stake_delegation",
        "path": "m/1852'/1815'/0'/2/0",
        "pool": "f61c42cbf7c8c53af3f520508212ad3e72f674f957fe23ff0acb49733c37b8f6",
    },
}

# todo: GK - add tests with byron addresses
# todo: GK - add tests with enterprise address
# todo: GK - add tests with bootstrap address
VALID_VECTORS = [
    # simple transaction without change outputs
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [],
        # input flow
        [[SWIPE, YES], [SWIPE, YES]],
        # tx hash
        "2131a3730ffd7ac43ce676df96d535c3d34cb37c1f26902a8f73db39bd1f4ff6",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018182582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa40102182a030aa100818258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d58408b35ca7a0850bbda33e64191fbb96fe7ce8054f53d2b617c1f8b1cffa022f5f714f8a6b16b02374794ab4c5118aacf729d18496ea8805a7690628540be89a001a0",
    ),
    # simple transaction with base address change output
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"], SAMPLE_OUTPUTS["simple_change_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [],
        # input flow
        [[SWIPE, YES], [SWIPE, YES]],
        # tx hash
        "520b8c28f7be5f977d930b6cbb191a29945fb8af048220f0136eeb5a145288ed",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa401825839009493315cd92eb5d8c4304e67b7e16ae36d61d34502694657811a2c8e32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc1a006ca79302182a030aa100818258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d5840b5f3053050410f0289f45a7da2e53d875c64673a9f57b0fd08151d5a114966b272eb9420e0ba57b019c01f7176e8727a7444097512563b62c70a93b6d065c206a0",
    ),
    # simple transaction with base address change output with staking key hash
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"], SAMPLE_OUTPUTS["staking_key_hash_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [],
        # input flow
        [[SWIPE, YES], [SWIPE, YES]],
        # tx hash
        "b6e3c0dc93e2b098acf3803ab1249c72145ae6d13a45dcab211567771cac2f23",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa401825839009493315cd92eb5d8c4304e67b7e16ae36d61d34502694657811a2c8e122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771a006ca79302182a030aa100818258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d58406ac17011b60b9b3a4360fb928a1f3b4767c85428891d0341d8e991db274c5929dd46e2f6c20258963d5ce452bd722c100ec297ad088e16bbf0f593c3863a410fa0",
    ),
    # simple transaction with pointer address change output
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"], SAMPLE_OUTPUTS["pointer_address_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [],
        # input flow
        [[SWIPE, YES], [SWIPE, YES]],
        # tx hash
        "02d5a72fe0278aaa4441dadd883b323e7d82e3389022b9f901c2aafc6e187f7d",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa401825820409493315cd92eb5d8c4304e67b7e16ae36d61d34502694657811a2c8e0102031a006ca79302182a030aa100818258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d5840d329bf9a560d5c246d8fed920601a91d3124cf78516fa353ada22263f834d81d376c6f96166cda9945d157b05ea4168253345c70b9a636a835ce7a6122c9640ea0",
    ),
    # transaction with stake registration certificate
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [SAMPLE_CERTIFICATES["stake_registration"]],
        # input flow
        [[SWIPE, YES], [YES], [SWIPE, YES]],
        # tx hash
        "7f097da356d2ec5210fe805f4165c6a34eaec7d11af20c8ce601eb7e263412d9",
        # tx body
        "83a500818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018182582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa40102182a030a0481820082005820b1b0fe2591f26ec5c2b4ff8b4c76fe727a465e965dc548f213cc0d2979dc2641a100818258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d5840bd1f51a2c112dd8adbcda5099ba5c2e264ecea926478cf070859a297b376d568ed1df5b315747ef5252182e5836d0744d9f5f3956d62cd96519f512036091605a0",
    ),
    # transaction with stake registration and stake delegation certificates
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [
            SAMPLE_CERTIFICATES["stake_registration"],
            SAMPLE_CERTIFICATES["stake_delegation"],
        ],
        # input flow
        [[SWIPE, YES], [YES], [SWIPE, YES], [SWIPE, YES]],
        # tx hash
        "decaa9fca7de58c8bed4f703f9688b1ea7884945aacd9f5b75f9fd6e78daf081",
        # tx body
        "83a500818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018182582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa40102182a030a0482820082005820b1b0fe2591f26ec5c2b4ff8b4c76fe727a465e965dc548f213cc0d2979dc2641820282005820b1b0fe2591f26ec5c2b4ff8b4c76fe727a465e965dc548f213cc0d2979dc2641a100828258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d5840db225dd449c0d01f0ad9468e8d78564bd6172d8390f36c0c243d044d0df784f8ab8523e36bffd2b3428fb4febcc335faf2a6c4d424ab964dda27f40f3f26a007825821012c041c9c6a676ac54d25e2fdce44c56581e316ae43adc4c7bf17f23214d8d89258407a69ac1f77be9d6c6df122582cee2038efbd2deccedcc8e0a9f0310a43e03692b3a36a69d97cc6d6b4111b7dfb7eefcfedb2df83b3ada695342c69a8edd9c807a0",
    ),
    # transaction with stake deregistration
    (
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["simple_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # certificates
        [SAMPLE_CERTIFICATES["stake_deregistration"]],
        # input flow
        [[SWIPE, YES], [YES], [SWIPE, YES]],
        # tx hash
        "b4115575a6e787971d54e13bc2c73d84d2ab3ddbe10ad1ee4e44326ce69529a9",
        # tx body
        "83a500818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018182582161a6274badf4c9ca583df893a73139625ff4dc73aaa3082e67d6d5d08e0ce3daa40102182a030a0481820182005820b1b0fe2591f26ec5c2b4ff8b4c76fe727a465e965dc548f213cc0d2979dc2641a100828258210173fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d5840fc0e5c39bc2166127f1148e8933aebdee09020d8d4233580d549e9a594dcd334a849e38e51b3295f6fd88ff59fa079ccca52c590b1630e79d6ca376c59f4870d825821012c041c9c6a676ac54d25e2fdce44c56581e316ae43adc4c7bf17f23214d8d8925840497e3365812200aaf9daf3f51e0c84a6c913e32b6eb587a8846d4f3baa432140d8512ceb3c9e80c37047997acf56070d8c65a1d72c62ea2ee61d80fda9b52c01a0",
    ),
]

# todo: GK - add invalid tests


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,fee,ttl,certificates,input_flow_sequence,tx_hash,tx_body",
    VALID_VECTORS,
)
@pytest.mark.setup_client(mnemonic=SHELLEY_TEST_VECTORS_MNEMONIC)
def test_cardano_sign_tx(
    client,
    protocol_magic,
    inputs,
    outputs,
    fee,
    ttl,
    certificates,
    input_flow_sequence,
    tx_hash,
    tx_body,
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]
    certificates = [cardano.create_certificate(c) for c in certificates]

    expected_responses = []
    # todo: refactor?
    for i in range(len(input_flow_sequence)):
        expected_responses.append(
            messages.ButtonRequest(code=messages.ButtonRequestType.Other)
        )

    expected_responses.append(messages.CardanoSignedTx())

    # todo: refactor?
    def input_flow():
        for sub_sequence in input_flow_sequence:
            yield
            for step in sub_sequence:
                if step == SWIPE:
                    client.debug.swipe_up()
                elif step == YES:
                    client.debug.press_yes()

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client, inputs, outputs, fee, ttl, certificates, protocol_magic
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.tx_body.hex() == tx_body
