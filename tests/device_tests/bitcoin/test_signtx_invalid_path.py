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

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings
from .signtx import forge_prevtx, request_input

B = messages.ButtonRequestType

# address at seed "all all all..." path m/44h/0h/0h/0/0
INPUT_ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
PREV_HASH, PREV_TX = forge_prevtx([(INPUT_ADDRESS, 390_000)])
PREV_TXES = {PREV_HASH: PREV_TX}


# Litecoin does not have strong replay protection using SIGHASH_FORKID,
# spending from Bitcoin path should fail.
@pytest.mark.altcoin
def test_invalid_path_fail(session: Session):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),
        amount=390_000,
        prev_hash=PREV_HASH,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
    out1 = messages.TxOutputType(
        address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
        amount=390_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as exc:
        btc.sign_tx(session, "Litecoin", [inp1], [out1], prev_txes=PREV_TXES)

    assert exc.value.code == messages.FailureType.DataError
    assert exc.value.message.endswith("Forbidden key path")


# Litecoin does not have strong replay protection using SIGHASH_FORKID, but
# spending from Bitcoin path should pass with safety checks set to prompt.
@pytest.mark.altcoin
def test_invalid_path_prompt(session: Session):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),
        amount=390_000,
        prev_hash=PREV_HASH,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
    out1 = messages.TxOutputType(
        address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
        amount=390_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    device.apply_settings(
        session, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )

    with session.client as client:
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session.client)
            client.set_input_flow(IF.get())

        btc.sign_tx(session, "Litecoin", [inp1], [out1], prev_txes=PREV_TXES)


# Bcash does have strong replay protection using SIGHASH_FORKID,
# spending from Bitcoin path should work.
@pytest.mark.altcoin
def test_invalid_path_pass_forkid(session: Session):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),
        amount=390_000,
        prev_hash=PREV_HASH,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 to cashaddr format
    out1 = messages.TxOutputType(
        address="bitcoincash:qr0fk25d5zygyn50u5w7h6jkvctas52n0qxff9ja6r",
        amount=390_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.client as client:
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session.client)
            client.set_input_flow(IF.get())

        btc.sign_tx(session, "Bcash", [inp1], [out1], prev_txes=PREV_TXES)


def test_attack_path_segwit(session: Session):
    # Scenario: The attacker falsely claims that the transaction uses Testnet paths to
    # avoid the path warning dialog, but in step6_sign_segwit_inputs() uses Bitcoin paths
    # to get a valid signature.

    device.apply_settings(
        session, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )

    # Generate keys
    address_a = btc.get_address(
        session,
        "Testnet",
        parse_path("m/84h/0h/0h/0/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    address_b = btc.get_address(
        session,
        "Testnet",
        parse_path("m/84h/0h/1h/0/1"),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    prev_hash, prev_tx = forge_prevtx(
        [(address_a, 9_426), (address_b, 7_086)], network="testnet"
    )

    inp1 = messages.TxInputType(
        # The actual input that the attacker wants to get signed.
        address_n=parse_path("m/84h/0h/0h/0/0"),
        amount=9_426,
        prev_hash=prev_hash,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        # The actual input that the attacker wants to get signed.
        # We need this one to be from a different account, so that the match checker
        # allows the transaction to pass.
        address_n=parse_path("m/84h/0h/1h/0/1"),
        amount=7_086,
        prev_hash=prev_hash,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    out1 = messages.TxOutputType(
        # Attacker's Mainnet address encoded as Testnet.
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=9_426 + 7_086 - 500,
    )

    attack_count = 6

    def attack_processor(msg):
        nonlocal attack_count
        # Make the inputs look like they are coming from Testnet paths until we reach the
        # signing phase.
        if attack_count > 0 and msg.tx.inputs and msg.tx.inputs[0] in (inp1, inp2):
            attack_count -= 1
            msg.tx.inputs[0].address_n[1] = H_(1)

        return msg

    with session.client as client:
        client.set_filter(messages.TxAck, attack_processor)
        with pytest.raises(TrezorFailure):
            btc.sign_tx(
                session, "Testnet", [inp1, inp2], [out1], prev_txes={prev_hash: prev_tx}
            )


def test_invalid_path_fail_asap(session: Session):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/0"),
        amount=1_000_000,
        prev_hash=b"\x42" * 32,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        sequence=4_294_967_293,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/84h/0h/0h/1/0"),
        amount=1_000_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    with session.client as client:
        client.set_expected_responses(
            [
                request_input(0),
                messages.Failure(code=messages.FailureType.DataError),
            ]
        )
        try:
            btc.sign_tx(session, "Testnet", [inp1], [out1])
        except TrezorFailure:
            pass
