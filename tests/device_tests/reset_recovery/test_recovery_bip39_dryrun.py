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

from typing import Any, List

import pytest

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ... import buttons
from ...common import MNEMONIC12


def do_recover_legacy(client: Client, mnemonic: List[str], **kwargs: Any):
    def input_callback(_):
        word, pos = client.debug.read_recovery_word()
        if pos != 0 and pos is not None:
            word = mnemonic[pos - 1]
            mnemonic[pos - 1] = None
            assert word is not None

        return word

    ret = device.recover(
        client,
        dry_run=True,
        word_count=len(mnemonic),
        type=messages.RecoveryDeviceType.ScrambledWords,
        input_callback=input_callback,
        show_tutorial=False,
        **kwargs
    )
    # if the call succeeded, check that all words have been used
    assert all(m is None for m in mnemonic)
    return ret


def do_recover_core(client: Client, mnemonic: List[str], **kwargs: Any):
    layout = client.debug.wait_layout

    def input_flow():
        yield
        assert "check the recovery seed" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        assert "select the number of words" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        assert "SelectWordCount" in layout().text
        # click the number
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(len(mnemonic))
        client.debug.click(buttons.grid34(index % 3, index // 3))

        yield
        assert "enter your recovery seed" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        for word in mnemonic:
            client.debug.wait_layout()
            client.debug.input(word)

        yield
        client.debug.wait_layout()
        client.debug.click(buttons.OK)

    with client:
        client.watch_layout()
        client.set_input_flow(input_flow)
        return device.recover(client, dry_run=True, show_tutorial=False, **kwargs)


def do_recover_r(client: Client, mnemonic: List[str], **kwargs: Any):
    layout = client.debug.wait_layout

    def input_flow():
        yield
        assert "check the recovery seed" in layout().text
        client.debug.press_right()

        yield
        assert "select the number of words" in layout().text
        client.debug.press_yes()

        yield
        yield
        assert "NUMBER OF WORDS" in layout().text
        word_options = (12, 18, 20, 24, 33)
        index = word_options.index(len(mnemonic))
        for _ in range(index):
            client.debug.press_right()
        client.debug.input(str(len(mnemonic)))

        yield
        assert "enter your recovery seed" in layout().text
        client.debug.press_yes()

        yield
        client.debug.press_right()
        yield
        for word in mnemonic:
            assert "WORD" in layout().text
            client.debug.input(word)

        client.debug.wait_layout()
        client.debug.press_right()
        yield
        client.debug.press_yes()
        yield

    with client:
        client.watch_layout()
        client.set_input_flow(input_flow)
        return device.recover(client, dry_run=True, show_tutorial=False, **kwargs)


def do_recover(client: Client, mnemonic: List[str]):

    if client.features.model == "1":
        return do_recover_legacy(client, mnemonic)
    elif client.features.model == "R":
        return do_recover_r(client, mnemonic)
    else:
        return do_recover_core(client, mnemonic)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_dry_run(client: Client):
    ret = do_recover(client, MNEMONIC12.split(" "))
    assert isinstance(ret, messages.Success)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_seed_mismatch(client: Client):
    with pytest.raises(
        exceptions.TrezorFailure, match="does not match the one in the device"
    ):
        do_recover(client, ["all"] * 12)


@pytest.mark.skip_t2
@pytest.mark.skip_tr
def test_invalid_seed_t1(client: Client):
    with pytest.raises(exceptions.TrezorFailure, match="Invalid seed"):
        do_recover(client, ["stick"] * 12)


@pytest.mark.skip_t1
def test_invalid_seed_core(client: Client):
    layout = client.debug.wait_layout

    def input_flow_tt():
        yield
        assert "check the recovery seed" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        assert "select the number of words" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        assert "SelectWordCount" in layout().text
        # select 12 words
        client.debug.click(buttons.grid34(0, 2))

        yield
        assert "enter your recovery seed" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        for _ in range(12):
            assert layout().text == "< MnemonicKeyboard >"
            client.debug.input("stick")

        br = yield
        assert br.code == messages.ButtonRequestType.Warning
        assert "invalid recovery seed" in layout().get_content()
        client.debug.click(buttons.OK)

        yield
        # retry screen
        assert "select the number of words" in layout().get_content()
        client.debug.click(buttons.CANCEL)

        yield
        assert "ABORT SEED CHECK" == layout().get_title()
        client.debug.click(buttons.OK)

    def input_flow_tr():
        yield
        assert "check the recovery seed" in layout().text
        client.debug.press_right()

        yield
        assert "select the number of words" in layout().text
        client.debug.press_yes()

        yield
        yield
        assert "NUMBER OF WORDS" in layout().text
        # select 12 words
        client.debug.press_middle()

        yield
        assert "enter your recovery seed" in layout().text
        client.debug.press_yes()

        yield
        assert "WORD ENTERING" in layout().text
        client.debug.press_yes()

        yield
        for _ in range(12):
            assert "WORD" in layout().text
            client.debug.input("stick")

        br = yield
        assert br.code == messages.ButtonRequestType.Warning
        assert "invalid recovery seed" in layout().text
        client.debug.press_right()

        yield
        # retry screen
        assert "select the number of words" in layout().text
        client.debug.press_left()

        yield
        assert "abort" in layout().text
        client.debug.press_right()

    with client:
        client.watch_layout()
        if client.features.model == "T":
            client.set_input_flow(input_flow_tt)
        elif client.features.model == "R":
            client.set_input_flow(input_flow_tr)
        with pytest.raises(exceptions.Cancelled):
            return device.recover(client, dry_run=True, show_tutorial=False)


@pytest.mark.setup_client(uninitialized=True)
def test_uninitialized(client: Client):
    with pytest.raises(exceptions.TrezorFailure, match="not initialized"):
        do_recover(client, ["all"] * 12)


DRY_RUN_ALLOWED_FIELDS = (
    "dry_run",
    "word_count",
    "enforce_wordlist",
    "type",
    "show_tutorial",
)


def _make_bad_params():
    """Generate a list of field names that must NOT be set on a dry-run message,
    and default values of the appropriate type.
    """
    for field in messages.RecoveryDevice.FIELDS.values():
        if field.name in DRY_RUN_ALLOWED_FIELDS:
            continue

        if "int" in field.type:
            yield field.name, 1
        elif field.type == "bool":
            yield field.name, True
        elif field.type == "string":
            yield field.name, "test"
        else:
            # Someone added a field to RecoveryDevice of a type that has no assigned
            # default value. This test must be fixed.
            raise RuntimeError("unknown field in RecoveryDevice")


@pytest.mark.parametrize("field_name, field_value", _make_bad_params())
def test_bad_parameters(client: Client, field_name: str, field_value: Any):
    msg = messages.RecoveryDevice(
        dry_run=True,
        word_count=12,
        enforce_wordlist=True,
        type=messages.RecoveryDeviceType.ScrambledWords,
    )
    setattr(msg, field_name, field_value)
    with pytest.raises(
        exceptions.TrezorFailure, match="Forbidden field set in dry-run"
    ):
        client.call(msg)
