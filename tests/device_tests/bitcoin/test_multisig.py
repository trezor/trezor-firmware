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

from trezorlib import btc, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import MNEMONIC12
from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Bitcoin")
TX_API_TESTNET = TxCache("Testnet")

TXHASH_c6091a = bytes.fromhex(
    "c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"
)
TXHASH_509e08 = bytes.fromhex(
    "509e08424b047403b34dc83e9899e09185ea36791716e42c00a74e1f12bcb6ef"
)
TXHASH_6b07c1 = bytes.fromhex(
    "6b07c1321b52d9c85743f9695e13eb431b41708cdf4e1585258d51208e5b93fc"
)
TXHASH_0d5b56 = bytes.fromhex(
    "0d5b5648d47b5650edea1af3d47bbe5624213abb577cf1b1c96f98321f75cdbc"
)

pytestmark = pytest.mark.multisig


@pytest.mark.multisig
@pytest.mark.parametrize("chunkify", (True, False))
def test_2_of_3(client: Client, chunkify: bool):
    # input tx: 6b07c1321b52d9c85743f9695e13eb431b41708cdf4e1585258d51208e5b93fc

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/48h/1h/{index}h/0h"), coin_name="Testnet"
        ).node
        for index in range(1, 4)
    ]

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )
    # Let's go to sign with key 1
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/1h/0h/0/0"),
        amount=1_496_278,
        prev_hash=TXHASH_6b07c1,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",  # "44h/1h/0h/0/6"
        amount=1_496_278 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # Expected responses are the same for both two signings
    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(TXHASH_6b07c1),
        request_input(0, TXHASH_6b07c1),
        request_output(0, TXHASH_6b07c1),
        request_input(0),
        request_output(0),
        request_output(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)

        # Now we have first signature
        signatures1, _ = btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1],
            prev_txes=TX_API_TESTNET,
            chunkify=chunkify,
        )

    assert (
        signatures1[0].hex()
        == "304402206c99b48a12f340599076b93efdc2578b0cdeaedf9092aed628788f4ffc579a50022031b16212dd1f0f62f01bb5862b6d128276c7a5430746aa27a04ae0c8acbcb3b1"
    )

    # ---------------------------------------
    # Let's do second signature using 3rd key

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes,
        address_n=[0, 0],
        signatures=[
            signatures1[0],
            b"",
            b"",
        ],  # Fill signature from previous signing process
        m=2,
    )

    # Let's do a second signature with key 3
    inp3 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/3h/0h/0/0"),
        amount=1_496_278,
        prev_hash=TXHASH_6b07c1,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    with client:
        client.set_expected_responses(expected_responses)
        signatures2, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp3], [out1], prev_txes=TX_API_TESTNET
        )

    assert (
        signatures2[0].hex()
        == "304502210089153ad97c0d69656cd9bd9eb2056552acaec91365dd7ab31250f3f707123baa02200f884de63041d73bd20fbe8804c6036968d8149b7f46963a82b561cd8211ab08"
    )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/4123415574c16899b4bb5b691f9b65643dbe566a9b68e4e2e7a8b29c79c83f2b",
        tx_hex="0100000001fc935b8e20518d2585154edf8c70411b43eb135e69f94357c8d9521b32c1076b00000000fdfd000047304402206c99b48a12f340599076b93efdc2578b0cdeaedf9092aed628788f4ffc579a50022031b16212dd1f0f62f01bb5862b6d128276c7a5430746aa27a04ae0c8acbcb3b10148304502210089153ad97c0d69656cd9bd9eb2056552acaec91365dd7ab31250f3f707123baa02200f884de63041d73bd20fbe8804c6036968d8149b7f46963a82b561cd8211ab08014c69522103725d6c5253f2040a9a73af24bcc196bf302d6cc94374dd7197b138e10912670121038924e94fff15302a3fb45ad4fc0ed17178800f0f1c2bdacb1017f4db951aa9f12102aae8affd0eb8e1181d665daef4de1828f23053c548ec9bafc3a787f558aa014153aeffffffff01c6ad1600000000001976a9144cfc772f24b600762f905a1ee799ce0e9c26831f88ac00000000",
    )


@pytest.mark.multisig
def test_15_of_15(client: Client):
    # input tx: 0d5b5648d47b5650edea1af3d47bbe5624213abb577cf1b1c96f98321f75cdbc

    node = btc.get_public_node(
        client, parse_path("m/48h/1h/1h/0h"), coin_name="Testnet"
    ).node
    pubs = [messages.HDNodePathType(node=node, address_n=[0, x]) for x in range(15)]

    signatures = [b""] * 15

    out1 = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",  # "44h/1h/0h/0/6"
        amount=1_476_278 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    for x in range(15):
        multisig = messages.MultisigRedeemScriptType(
            pubkeys=pubs, signatures=signatures, m=15
        )

        inp1 = messages.TxInputType(
            address_n=parse_path(f"m/48h/1h/1h/0h/0/{x}"),
            amount=1_476_278,
            prev_hash=TXHASH_0d5b56,
            prev_index=0,
            script_type=messages.InputScriptType.SPENDMULTISIG,
            multisig=multisig,
        )

        with client:
            sig, serialized_tx = btc.sign_tx(
                client, "Testnet", [inp1], [out1], prev_txes=TX_API_TESTNET
            )
            signatures[x] = sig[0]

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/b41284067577e1266ad3632f7caffead5d58277cc35f42642455bfd2a3fa0325",
    )


@pytest.mark.multisig
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_missing_pubkey(client: Client):
    node = btc.get_public_node(
        client, parse_path("m/48h/0h/1h/0h/0"), coin_name="Bitcoin"
    ).node

    multisig = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=node, address_n=[1]),
            messages.HDNodePathType(node=node, address_n=[2]),
            messages.HDNodePathType(node=node, address_n=[3]),
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    # Let's go to sign with key 10, which is NOT in pubkeys
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/0h/1h/0h/0/10"),
        amount=100_000,
        prev_hash=TXHASH_c6091a,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        address="12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss",
        amount=100_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as exc:
        btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_API)

    if client.features.model == "1":
        assert exc.value.message.endswith("Failed to derive scriptPubKey")
    else:
        assert exc.value.message.endswith("Pubkey not found in multisig script")


@pytest.mark.multisig
def test_attack_change_input(client: Client):
    """
    In Phases 1 and 2 the attacker replaces a non-multisig input
    `input_real` with a multisig input `input_fake`, which allows the
    attacker to provide a 1-of-2 multisig change address. When `input_real`
    is provided in the signing phase, an error must occur.
    """
    address_n = parse_path("m/48h/1h/0h/1h/0/0")  # 2NErUdruXmM8o8bQySrzB3WdBRcmc5br4E8
    attacker_multisig_public_key = bytes.fromhex(
        "03653a148b68584acb97947344a7d4fd6a6f8b8485cad12987ff8edac874268088"
    )

    input_real = messages.TxInputType(
        address_n=address_n,
        prev_hash=TXHASH_509e08,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        amount=61_093,
    )

    multisig_fake = messages.MultisigRedeemScriptType(
        m=1,
        nodes=[
            btc.get_public_node(client, address_n, coin_name="Testnet").node,
            messages.HDNodeType(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=bytes(32),
                public_key=attacker_multisig_public_key,
            ),
        ],
        address_n=[],
    )

    input_fake = messages.TxInputType(
        address_n=address_n,
        prev_hash=input_real.prev_hash,
        prev_index=input_real.prev_index,
        script_type=input_real.script_type,
        multisig=multisig_fake,
        amount=input_real.amount,
    )

    output_payee = messages.TxOutputType(
        address="n2eMqTT929pb1RDNuqEnxdaLau1rxy3efi",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    output_change = messages.TxOutputType(
        address_n=address_n,
        amount=input_real.amount - output_payee.amount - 1_000,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        multisig=multisig_fake,
    )

    # Transaction can be signed without the attack processor
    with client:
        btc.sign_tx(
            client,
            "Testnet",
            [input_real],
            [output_payee, output_change],
            prev_txes=TX_API_TESTNET,
        )

    attack_count = 3

    def attack_processor(msg):
        nonlocal attack_count
        # replace the first input_real with input_fake
        if attack_count > 0 and msg.tx.inputs and msg.tx.inputs[0] == input_real:
            msg.tx.inputs[0] = input_fake
            attack_count -= 1
        return msg

    with client:
        client.set_filter(messages.TxAck, attack_processor)
        with pytest.raises(TrezorFailure):
            btc.sign_tx(
                client,
                "Testnet",
                [input_real],
                [output_payee, output_change],
                prev_txes=TX_API_TESTNET,
            )
