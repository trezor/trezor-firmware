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

from trezorlib import device, exceptions, messages

from .. import buttons
from ..common import MNEMONIC12


def do_recover_legacy(client, mnemonic, **kwargs):
    def input_callback(_):
        word, pos = client.debug.read_recovery_word()
        if pos != 0:
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
        **kwargs
    )
    # if the call succeeded, check that all words have been used
    assert all(m is None for m in mnemonic)
    return ret


def do_recover_core(client, mnemonic, **kwargs):
    def input_flow():
        yield
        layout = client.debug.wait_layout()
        assert "check the recovery seed" in layout.text.replace("\n", " ")
        client.debug.click(buttons.OK)

        yield
        layout = client.debug.wait_layout()
        assert "Select number of words" in layout.text
        client.debug.click(buttons.OK)

        yield
        layout = client.debug.wait_layout()
        assert layout.text == "WordSelector"
        # click the number
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(len(mnemonic))
        client.debug.click(buttons.grid34(index % 3, index // 3))

        yield
        layout = client.debug.wait_layout()
        assert "Enter recovery seed" in layout.text
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
        return device.recover(client, dry_run=True, **kwargs)


def do_recover(client, mnemonic):
    if client.features.model == "1":
        return do_recover_legacy(client, mnemonic)
    else:
        return do_recover_core(client, mnemonic)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_dry_run(client):
    ret = do_recover(client, MNEMONIC12.split(" "))
    assert isinstance(ret, messages.Success)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_seed_mismatch(client):
    with pytest.raises(
        exceptions.TrezorFailure, match="does not match the one in the device"
    ):
        do_recover(client, ["all"] * 12)


@pytest.mark.skip_t2
def test_invalid_seed_t1(client):
    with pytest.raises(exceptions.TrezorFailure, match="Invalid seed"):
        do_recover(client, ["stick"] * 12)


@pytest.mark.skip_t1
def test_invalid_seed_core(client):
    def input_flow():
        yield
        layout = client.debug.wait_layout()
        assert "check the recovery seed" in layout.text.replace("\n", " ")
        client.debug.click(buttons.OK)

        yield
        layout = client.debug.wait_layout()
        assert "Select number of words" in layout.text
        client.debug.click(buttons.OK)

        yield
        layout = client.debug.wait_layout()
        assert layout.text == "WordSelector"
        # select 12 words
        client.debug.click(buttons.grid34(0, 2))

        yield
        layout = client.debug.wait_layout()
        assert "Enter recovery seed" in layout.text
        client.debug.click(buttons.OK)

        yield
        for _ in range(12):
            layout = client.debug.wait_layout()
            assert layout.text == "Bip39Keyboard"
            client.debug.input("stick")

        code = yield
        layout = client.debug.wait_layout()
        assert code == messages.ButtonRequestType.Warning
        assert "invalid recovery seed" in layout.text
        client.debug.click(buttons.OK)

        yield
        # retry screen
        layout = client.debug.wait_layout()
        assert "Select number of words" in layout.text
        client.debug.click(buttons.CANCEL)

        yield
        layout = client.debug.wait_layout()
        assert "abort" in layout.text
        client.debug.click(buttons.OK)

    with client:
        client.watch_layout()
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            return device.recover(client, dry_run=True)


@pytest.mark.setup_client(uninitialized=True)
def test_uninitialized(client):
    with pytest.raises(exceptions.TrezorFailure, match="not initialized"):
        do_recover(client, ["all"] * 12)


DRY_RUN_ALLOWED_FIELDS = ("dry_run", "word_count", "enforce_wordlist", "type")


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
def test_bad_parameters(client, field_name, field_value):
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
