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

from typing import Optional

import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import H_, parse_path

from ... import bip32
from ...common import MNEMONIC12, is_core
from ...input_flows import InputFlowConfirmAllWarnings
from .signtx import (
    forge_prevtx,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType

pytestmark = [pytest.mark.multisig, pytest.mark.setup_client(mnemonic=MNEMONIC12)]


NODE_EXT1 = bip32.deserialize(
    "xpub69qexv5TppjJQtXwSGeGXNtgGWyUzvsHACMt4Rr61Be4CmCf55eFcuXX828aySNuNR7hQYUCvUgZpioNxfs2HTAZWUUSFywhErg7JfTPv3Y"
)
# m/1 => 02c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e
# m/2 => 0375b9dfaad928ce1a7eed88df7c084e67d99e9ab74332419458a9a45779706801

NODE_EXT2 = bip32.deserialize(
    "xpub69qexv5TppjJRiLLK2K1FZNCFcErkXprCo3jabCXMiqX5CFF4LHedwcXvXkTuBL9tFLWVxuGWrdeerXjiWpC1gynTNUaySDsr8SU5xMpj5R"
)
# m/1 => 0388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1
# m/2 => 03a04f945d5a3685729dde697d574076de4bdf38e904f813b22a851548e1110fc0

NODE_EXT3 = bip32.deserialize(
    "xpub69qexv5TppjJVYtxFKSBFxcVGyaC8VJDa1RugAYwEDLVUBuaXrVgznvQB44piM8MRerfVf1pNCBK1L1NzhyKd4Ay25BVZX3S8twWfZDxmz7"
)
# m/1 => 02e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648
# m/2 => 03928301ffb8c0d7a364b794914c716ba3107cc78a6fe581028b0d8638b22e8573

NODE_INT = bip32.deserialize(
    "xpub69qexv5TppjJNEK5bfX8vQ6ASXDUQ5PohSajrHgeknHZ4SJipn7edmpRmiiBLLDtPur71mekZFazhgas8rkUMnS7quk5qp64TLLV8ShrxZJ"
)
# m/1 => 03f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff35
# m/2 => 038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3

multisig_in1 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
    address_n=[0, 0],
    signatures=[b"", b"", b""],
    m=2,
)

multisig_in2 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
    address_n=[0, 1],
    signatures=[b"", b"", b""],
    m=2,
)

multisig_in3 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT1, NODE_EXT3, NODE_INT],
    address_n=[0, 1],
    signatures=[b"", b"", b""],
    m=2,
)

prev_hash_1, prev_tx_1 = forge_prevtx(
    [("3Ltgk5WPUMLcT2QvwRXKj9CWsYuAKqeHJ8", 50_000_000)]
)
INP1 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 0],
    amount=50_000_000,
    prev_hash=prev_hash_1,
    prev_index=0,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in1,
)

prev_hash_2, prev_tx_2 = forge_prevtx(
    [("3Md42fbNjSH3qwnj5jDvT6CSzJKVXHiXSc", 34_500_000)]
)
INP2 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 1],
    amount=34_500_000,
    prev_hash=prev_hash_2,
    prev_index=0,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in2,
)

prev_hash_3, prev_tx_3 = forge_prevtx(
    [("35PBSvszuvxhEDypGYcUhEQDigvKY8C5Rc", 55_500_000)]
)
INP3 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 1],
    amount=55_500_000,
    prev_hash=prev_hash_3,
    prev_index=0,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in3,
)

TX_API = {prev_hash_1: prev_tx_1, prev_hash_2: prev_tx_2, prev_hash_3: prev_tx_3}


def _responses(
    client: Client,
    INP1: messages.TxInputType,
    INP2: messages.TxInputType,
    change_indices: Optional[list[int]] = None,
    foreign_indices: Optional[list[int]] = None,
):
    if change_indices is None:
        change_indices = []
    if foreign_indices is None:
        foreign_indices = []

    resp = [
        request_input(0),
        request_input(1),
        request_output(0),
    ]

    if 1 in foreign_indices:
        resp.append(messages.ButtonRequest(code=B.UnknownDerivationPath))
    if 1 not in change_indices:
        resp.append(messages.ButtonRequest(code=B.ConfirmOutput))
        if is_core(client):
            resp.append(messages.ButtonRequest(code=B.ConfirmOutput))

    resp.append(request_output(1))

    if 2 in foreign_indices:
        resp.append(messages.ButtonRequest(code=B.UnknownDerivationPath))
    if 2 not in change_indices:
        resp.append(messages.ButtonRequest(code=B.ConfirmOutput))
        if is_core(client):
            resp.append(messages.ButtonRequest(code=B.ConfirmOutput))

    resp += [
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(INP1.prev_hash),
        request_input(0, INP1.prev_hash),
        request_output(0, INP1.prev_hash),
        request_input(1),
        request_meta(INP2.prev_hash),
        request_input(0, INP2.prev_hash),
        request_output(0, INP2.prev_hash),
        request_input(0),
        request_input(1),
        request_output(0),
        request_output(1),
        request_input(0),
        request_input(1),
        request_output(0),
        request_output(1),
        request_output(0),
        request_output(1),
        request_finished(),
    ]
    return resp


# both outputs are external
def test_external_external(client: Client):
    out1 = messages.TxOutputType(
        address="1F8yBZB2NZhPZvJekhjTwjhQRRvQeTjjXr",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1H7uXJQTVwXca2BXF2opTrvuZapk8Cm8zY",
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(client, INP1, INP2))
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# first external, second internal
def test_external_internal(client: Client):
    out1 = messages.TxOutputType(
        address="1F8yBZB2NZhPZvJekhjTwjhQRRvQeTjjXr",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/45h/0/1/1"),
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            _responses(
                client,
                INP1,
                INP2,
                change_indices=[] if is_core(client) else [2],
                foreign_indices=[2],
            )
        )
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# first internal, second external
def test_internal_external(client: Client):
    out1 = messages.TxOutputType(
        address_n=parse_path("m/45h/0/1/0"),
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1H7uXJQTVwXca2BXF2opTrvuZapk8Cm8zY",
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            _responses(
                client,
                INP1,
                INP2,
                change_indices=[] if is_core(client) else [1],
                foreign_indices=[1],
            )
        )
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# both outputs are external
def test_multisig_external_external(client: Client):
    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(client, INP1, INP2))
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# inputs match, change matches (first is change)
def test_multisig_change_match_first(client: Client):
    multisig_out1 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out1,
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            _responses(client, INP1, INP2, change_indices=[1])
        )
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# inputs match, change matches (second is change)
def test_multisig_change_match_second(client: Client):
    multisig_out2 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
        address_n=[1, 1],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 1],
        multisig=multisig_out2,
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    with client:
        client.set_expected_responses(
            _responses(client, INP1, INP2, change_indices=[2])
        )
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# inputs match, change mismatches (second tries to be change but isn't)
def test_multisig_mismatch_multisig_change(client: Client):
    multisig_out2 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT1, NODE_INT, NODE_EXT3],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out2,
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    with client:
        client.set_expected_responses(_responses(client, INP1, INP2))
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# inputs match, change mismatches (second tries to be change but isn't)
@pytest.mark.models(skip="legacy", reason="Not fixed")
def test_multisig_mismatch_multisig_change_different_paths(client: Client):
    multisig_out2 = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=NODE_EXT1, address_n=[1, 0]),
            messages.HDNodePathType(node=NODE_EXT2, address_n=[1, 1]),
            messages.HDNodePathType(node=NODE_INT, address_n=[1, 2]),
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 2],
        multisig=multisig_out2,
        amount=44_000_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    with client:
        client.set_expected_responses(_responses(client, INP1, INP2))
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )


# inputs mismatch, change matches with first input
def test_multisig_mismatch_inputs(client: Client):
    multisig_out1 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT2, NODE_EXT1, NODE_INT],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out1,
        amount=40_000_000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=65_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(client, INP1, INP3))
        btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP3],
            [out1, out2],
            prev_txes=TX_API,
        )
