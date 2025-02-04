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

from typing import Any

import pytest

from trezorlib import device, exceptions, messages, models
from trezorlib.debuglink import SessionDebugWrapper as Session

from ...common import MNEMONIC12
from ...input_flows import (
    InputFlowBip39RecoveryDryRun,
    InputFlowBip39RecoveryDryRunInvalid,
)


def do_recover_legacy(session: Session, mnemonic: list[str]):
    def input_callback(_):
        word, pos = session.client.debug.read_recovery_word()
        if pos != 0 and pos is not None:
            word = mnemonic[pos - 1]
            mnemonic[pos - 1] = None
            assert word is not None

        return word

    ret = device.recover(
        session,
        type=messages.RecoveryType.DryRun,
        word_count=len(mnemonic),
        input_method=messages.RecoveryDeviceInputMethod.ScrambledWords,
        input_callback=input_callback,
    )
    # if the call succeeded, check that all words have been used
    assert all(m is None for m in mnemonic)
    return ret


def do_recover_core(session: Session, mnemonic: list[str], mismatch: bool = False):
    with session.client as client:
        client.watch_layout()
        IF = InputFlowBip39RecoveryDryRun(client, mnemonic, mismatch=mismatch)
        client.set_input_flow(IF.get())
        return device.recover(session, type=messages.RecoveryType.DryRun)


def do_recover(session: Session, mnemonic: list[str], mismatch: bool = False):
    if session.model is models.T1B1:
        return do_recover_legacy(session, mnemonic)
    else:
        return do_recover_core(session, mnemonic, mismatch)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_dry_run(session: Session):
    ret = do_recover(session, MNEMONIC12.split(" "))
    assert isinstance(ret, messages.Success)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_seed_mismatch(session: Session):
    with pytest.raises(
        exceptions.TrezorFailure, match="does not match the one in the device"
    ):
        do_recover(session, ["all"] * 12, mismatch=True)


@pytest.mark.models("legacy")
def test_invalid_seed_t1(session: Session):
    with pytest.raises(exceptions.TrezorFailure, match="Invalid seed"):
        do_recover(session, ["stick"] * 12)


@pytest.mark.models("core")
def test_invalid_seed_core(session: Session):
    with session, session.client as client:
        client.watch_layout()
        IF = InputFlowBip39RecoveryDryRunInvalid(session)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            return device.recover(
                session,
                type=messages.RecoveryType.DryRun,
            )


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_uninitialized(session: Session):
    with pytest.raises(exceptions.TrezorFailure, match="not initialized"):
        do_recover(session, ["all"] * 12)


DRY_RUN_ALLOWED_FIELDS = (
    "type",
    "word_count",
    "enforce_wordlist",
    "input_method",
    "show_tutorial",
)


def _make_bad_params():
    """Generate a list of field names that must NOT be set on a dry-run message,
    and default values of the appropriate type.
    """
    for field in messages.RecoveryDevice.FIELDS.values():
        # language is not supported anymore:
        if field.name == "language":
            continue

        if field.name in DRY_RUN_ALLOWED_FIELDS:
            continue

        if field.py_type is int:
            yield field.name, 1
        elif field.py_type is bool:
            yield field.name, True
        elif field.py_type is str:
            yield field.name, "test"
        elif field.py_type is messages.RecoveryType:
            yield field.name, 1
        else:
            # Someone added a field to RecoveryDevice of a type that has no assigned
            # default value. This test must be fixed.
            raise RuntimeError("unknown field in RecoveryDevice")


@pytest.mark.parametrize("field_name, field_value", _make_bad_params())
def test_bad_parameters(session: Session, field_name: str, field_value: Any):
    msg = messages.RecoveryDevice(
        type=messages.RecoveryType.DryRun,
        word_count=12,
        enforce_wordlist=True,
        input_method=messages.RecoveryDeviceInputMethod.ScrambledWords,
    )
    setattr(msg, field_name, field_value)
    with pytest.raises(
        exceptions.TrezorFailure,
        match="Forbidden field set in dry-run",
    ):
        session.call(msg)
