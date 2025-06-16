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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path


def test_p2wpkh_ownership_id(session: Session):
    ownership_id = btc.get_ownership_id(
        session,
        "Bitcoin",
        parse_path("m/84h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    assert (
        ownership_id.hex()
        == "a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad5707"
    )


def test_p2tr_ownership_id(session: Session):
    ownership_id = btc.get_ownership_id(
        session,
        "Bitcoin",
        parse_path("m/86h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    assert (
        ownership_id.hex()
        == "dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec"
    )


def test_attack_ownership_id(session: Session):
    # Multisig with global suffix specification.
    # Use account numbers 1, 2 and 3 to create a valid multisig,
    # but not containing the keys from account 0 used below.
    nodes = [
        btc.get_public_node(session, parse_path(f"m/84h/0h/{i}h")).node
        for i in range(1, 4)
    ]
    multisig1 = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )

    # Multisig with per-node suffix specification.
    node = btc.get_public_node(
        session, parse_path("m/84h/0h/0h/0"), coin_name="Bitcoin"
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
                session,
                "Bitcoin",
                parse_path("m/84h/0h/0h/0/0"),
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDWITNESS,
            )


def test_p2wpkh_ownership_proof(session: Session):
    ownership_proof, _ = btc.get_ownership_proof(
        session,
        "Bitcoin",
        parse_path("m/84h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    assert (
        ownership_proof.hex()
        == "534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100c0dc28bb563fc5fea76cacff75dba9cb4122412faae01937cdebccfb065f9a7002202e980bfbd8a434a7fc4cd2ca49da476ce98ca097437f8159b1a386b41fcdfac50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )


def test_p2tr_ownership_proof(session: Session):
    ownership_proof, _ = btc.get_ownership_proof(
        session,
        "Bitcoin",
        parse_path("m/86h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    assert (
        ownership_proof.hex()
        == "534c00190001dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec000140647d6af883107a870417e808abe424882bd28ee04a28ba85a7e99400e1b9485075733695964c2a0fa02d4439ab80830e9566ccbd10f2597f5513eff9f03a0497"
    )


def test_fake_ownership_id(session: Session):
    with pytest.raises(TrezorFailure, match="Invalid ownership identifier"):
        btc.get_ownership_proof(
            session,
            "Bitcoin",
            parse_path("m/84h/0h/0h/1/0"),
            script_type=messages.InputScriptType.SPENDWITNESS,
            ownership_ids=[
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"
            ],
        )


def test_confirm_ownership_proof(session: Session):
    ownership_proof, _ = btc.get_ownership_proof(
        session,
        "Bitcoin",
        parse_path("m/84h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
    )

    assert (
        ownership_proof.hex()
        == "534c00190101a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad5707000247304402201c8d141bcb99660d5de876e51d929abd2954a2eb79adde83d25cc5e94f085ace02207b14736cd0515a11571bcecfbd44f11ca8a2d661b5235fd27837b74ca5071a120121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )


def test_confirm_ownership_proof_with_data(session: Session):
    ownership_proof, _ = btc.get_ownership_proof(
        session,
        "Bitcoin",
        parse_path("m/84h/0h/0h/1/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        user_confirmation=True,
        commitment_data=b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
    )

    assert (
        ownership_proof.hex()
        == "534c00190101a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100b41c51d130d1e4e179679734b7fcb39abe8859727de10a782fac3f9bae82c31802205b0697eb1c101a1f5a3b103b7b6c34568adface1dbbb3512b783c66bb52f0c920121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
    )
