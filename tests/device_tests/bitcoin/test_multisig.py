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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path, tx_hash

from ...common import MNEMONIC12
from ...tx_cache import TxCache
from ..signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Bitcoin")

TXHASH_c6091a = bytes.fromhex(
    "c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"
)
TXHASH_6189e3 = bytes.fromhex(
    "6189e3febb5a21cee8b725aa1ef04ffce7e609448446d3a8d6f483c634ef5315"
)
TXHASH_fbbff7 = bytes.fromhex(
    "fbbff7f3c85f8067453d7c062bd5efb8ad839953376ae5eceaf92774102c6e39"
)

pytestmark = pytest.mark.multisig


def test_2_of_3(client):
    nodes = [
        btc.get_public_node(client, parse_path(f"48'/0'/{index}'/0'")).node
        for index in range(1, 4)
    ]

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )
    # Let's go to sign with key 1
    inp1 = messages.TxInputType(
        address_n=parse_path("48'/0'/1'/0'/0/0"),
        amount=100000,
        prev_hash=TXHASH_c6091a,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        address="12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss",
        amount=100000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_c6091a),
                request_input(0, TXHASH_c6091a),
                request_output(0, TXHASH_c6091a),
                request_output(1, TXHASH_c6091a),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )

        # Now we have first signature
        signatures1, _ = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_API
        )

    assert (
        signatures1[0].hex()
        == "30450221009276eea820aa54a24bd9f1a056cb09a15f50c0816570a7c7878bd1c5ee7248540220677d200aec5e2f25bcf4000bdfab3faa9e1746d7f80c4ae4bfa1f5892eb5dcbf"
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
        address_n=parse_path("48'/0'/3'/0'/0/0"),
        amount=100000,
        prev_hash=TXHASH_c6091a,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_c6091a),
                request_input(0, TXHASH_c6091a),
                request_output(0, TXHASH_c6091a),
                request_output(1, TXHASH_c6091a),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        signatures2, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp3], [out1], prev_txes=TX_API
        )

    assert (
        signatures2[0].hex()
        == "3045022100c2a9fbfbff1be87036d8a6a22745512b158154f7f3d8f4cad4ba7ed130b37b83022058f5299b4c26222588dcc669399bd88b6f2bc6e04b48276373683853187a4fd6"
    )

    assert (
        serialized_tx.hex()
        == "010000000152ba4dfcde9c4bed88f55479cdea03e711ae586e9a89352a98230c4cdf1a09c601000000fdfe00004830450221009276eea820aa54a24bd9f1a056cb09a15f50c0816570a7c7878bd1c5ee7248540220677d200aec5e2f25bcf4000bdfab3faa9e1746d7f80c4ae4bfa1f5892eb5dcbf01483045022100c2a9fbfbff1be87036d8a6a22745512b158154f7f3d8f4cad4ba7ed130b37b83022058f5299b4c26222588dcc669399bd88b6f2bc6e04b48276373683853187a4fd6014c69522103dc0ff15b9c85c0d2c87099758bf47d36229c2514aeefcf8dea123f0f93c679762102bfe426e8671601ad46d54d09ee15aa035610d36d411961c87474908d403fbc122102a5d57129c6c96df663ad29492aa18605dad97231e043be8a92f9406073815c5d53aeffffffff01a0860100000000001976a91412e8391ad256dcdc023365978418d658dfecba1c88ac00000000"
    )


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_15_of_15(client):
    node = btc.get_public_node(
        client, parse_path("48h/0h/1h/0h"), coin_name="Bitcoin"
    ).node
    pubs = [messages.HDNodePathType(node=node, address_n=[0, x]) for x in range(15)]

    signatures = [b""] * 15

    out1 = messages.TxOutputType(
        address="17kTB7qSk3MupQxWdiv5ZU3zcrZc2Azes1",
        amount=10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    for x in range(15):
        multisig = messages.MultisigRedeemScriptType(
            pubkeys=pubs, signatures=signatures, m=15
        )

        inp1 = messages.TxInputType(
            address_n=parse_path(f"48h/0h/1h/0h/0/{x}"),
            amount=20000,
            prev_hash=TXHASH_6189e3,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDMULTISIG,
            multisig=multisig,
        )

        with client:
            sig, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_API
            )
            signatures[x] = sig[0]

    assert (
        tx_hash(serialized_tx).hex()
        == "63b16e3107df552c5c74bb5d91bb8fcd0069bac461fb42ebef982c5b2cfc4cf4"
    )


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_missing_pubkey(client):
    node = btc.get_public_node(
        client, parse_path("48h/0h/1h/0h/0"), coin_name="Bitcoin"
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
        address_n=parse_path("48h/0h/1h/0h/0/10"),
        amount=100000,
        prev_hash=TXHASH_c6091a,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        address="12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss",
        amount=100000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as exc:
        btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_API)

    if client.features.model == "1":
        assert exc.value.message.endswith("Failed to derive scriptPubKey")
    else:
        assert exc.value.message.endswith("Pubkey not found in multisig script")


def test_attack_change_input(client):
    """
    In Phases 1 and 2 the attacker replaces a non-multisig input
    `input_real` with a multisig input `input_fake`, which allows the
    attacker to provide a 1-of-2 multisig change address. When `input_real`
    is provided in the signing phase, an error must occur.
    """
    address_n = parse_path("48'/1'/0'/1'/0/0")
    attacker_multisig_public_key = bytes.fromhex(
        "03653a148b68584acb97947344a7d4fd6a6f8b8485cad12987ff8edac874268088"
    )

    input_real = messages.TxInputType(
        address_n=address_n,
        prev_hash=TXHASH_fbbff7,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        amount=1000000,
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
        amount=1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    output_change = messages.TxOutputType(
        address_n=address_n,
        amount=input_real.amount - output_payee.amount - 1000,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        multisig=multisig_fake,
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
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_fbbff7),
                request_input(0, TXHASH_fbbff7),
                request_output(0, TXHASH_fbbff7),
                request_output(1, TXHASH_fbbff7),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )

        with pytest.raises(TrezorFailure) as exc:
            btc.sign_tx(
                client,
                "Testnet",
                [input_real],
                [output_payee, output_change],
                prev_txes=TxCache("Testnet"),
            )
            # must not produce this tx:
            # 01000000000101396e2c107427f9eaece56a37539983adb8efd52b067c3d4567805fc8f3f7bffb01000000171600147a876a07b366f79000b441335f2907f777a0280bffffffff02e8030000000000001976a914e7c1345fc8f87c68170b3aa798a956c2fe6a9eff88ac703a0f000000000017a914a1261837f1b40e84346b1504ffe294e402965f2687024830450221009ff835e861be4e36ca1f2b6224aee2f253dfb9f456b13e4b1724bb4aaff4c9c802205e10679c2ead85743119f468cba5661f68b7da84dd2d477a7215fef98516f1f9012102af12ddd0d55e4fa2fcd084148eaf5b0b641320d0431d63d1e9a90f3cbd0d540700000000

        assert exc.value.code == messages.FailureType.ProcessError
        assert exc.value.message.endswith("Transaction has changed during signing")
