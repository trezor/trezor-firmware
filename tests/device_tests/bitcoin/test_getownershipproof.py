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
from trezorlib.tools import parse_path

pytestmark = pytest.mark.skip_t1


def test_p2wpkh_ownership_id(client):
    ownership_id = btc.get_ownership_id(
        client,
        "Bitcoin",
        parse_path("m/84'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    assert (
        ownership_id.hex()
        == "a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad5707"
    )


def test_p2tr_ownership_id(client):
    ownership_id = btc.get_ownership_id(
        client,
        "Bitcoin",
        parse_path("m/86'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    assert (
        ownership_id.hex()
        == "dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec"
    )


def test_attack_ownership_id(client):
    # Multisig with global suffix specification.
    # Use account numbers 1, 2 and 3 to create a valid multisig,
    # but not containing the keys from account 0 used below.
    nodes = [
        btc.get_public_node(client, parse_path(f"84'/0'/{i}'")).node
        for i in range(1, 4)
    ]
    multisig1 = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )

    # Multisig with per-node suffix specification.
    node = btc.get_public_node(
        client, parse_path("84h/0h/0h/0"), coin_name="Bitcoin"
    ).node
    multisig2 = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=node, address_n=[1]),
            messages.HDNodePathType(node=node, address_n=[2]),
            messages.HDNodePathType(node=node, address_n=[3]),
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    for multisig in (multisig1, multisig2):
        with pytest.raises(TrezorFailure):
            btc.get_ownership_id(
                client,
                "Bitcoin",
                parse_path("84'/0'/0'/0/0"),
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDWITNESS,
            )


def test_p2wpkh_ownership_proof(client):
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Bitcoin",
        parse_path("m/84'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    assert (
        ownership_proof.hex()
        == "534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100e5eaf2cb0a473b4545115c7b85323809e75cb106175ace38129fd62323d73df30220363dbc7acb7afcda022b1f8d97acb8f47c42043cfe0595583aa26e30bc8b3bb50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )


def test_p2tr_ownership_proof(client):
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Bitcoin",
        parse_path("m/86'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    assert (
        ownership_proof.hex()
        == "534c00190001dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec0001406cd08474ea019c9ab4b9b7b76ec03c4dd4db76abc3a460434a91cfc1b190174949eb7111c8e762407730a215421a0da0b5e01f48de62d7ccea0abea046e2a496"
    )


def test_fake_ownership_id(client):
    with pytest.raises(TrezorFailure, match="Invalid ownership identifier"):
        btc.get_ownership_proof(
            client,
            "Bitcoin",
            parse_path("m/84'/0'/0'/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            ownership_ids=[
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"
            ],
        )


def test_confirm_ownership_proof(client):
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Bitcoin",
        parse_path("m/84'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100fa4561d261464360f18af9668c19e1b07d58f76814623aa8e5c9b2d85bc211d002207f364096183f461be75f763d2f970df6ac9b30a5a39556a07cab9c6f4d7883a80121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )


def test_confirm_ownership_proof_with_data(client):
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Bitcoin",
        parse_path("m/84'/0'/0'/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
    )

    assert (
        ownership_proof.hex()
        == "534c00190101a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100ac67fde3f0c8443c2708b3e405b17c4c8a51e510132b4f35aa6d6782713a53280220616192365f6202ee3f050d4e0e13c38198156024ca978fbd2b8c89c8823bb3dd0121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )
