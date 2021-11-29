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
from mnemonic import Mnemonic

from trezorlib import messages

from ...common import generate_entropy

pytestmark = pytest.mark.skip_t2

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
STRENGTH = 128


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_skip_backup(client):
    ret = client.call_raw(
        messages.ResetDevice(
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            language="en-US",
            label="test",
            skip_backup=True,
        )
    )

    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    internal_entropy = client.debug.state().reset_entropy
    ret = client.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))
    assert isinstance(ret, messages.Success)

    # Check if device is properly initialized
    ret = client.call_raw(messages.Initialize())
    assert ret.initialized is True
    assert ret.needs_backup is True
    assert ret.unfinished_backup is False
    assert ret.no_backup is False

    # Generate mnemonic locally
    entropy = generate_entropy(STRENGTH, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # start Backup workflow
    ret = client.call_raw(messages.BackupDevice())

    mnemonic = []
    for _ in range(STRENGTH // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(client.debug.read_reset_word())
        client.debug.press_yes()
        client.call_raw(messages.ButtonAck())

    mnemonic = " ".join(mnemonic)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    mnemonic = []
    for _ in range(STRENGTH // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(client.debug.read_reset_word())
        client.debug.press_yes()
        ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.Success)

    mnemonic = " ".join(mnemonic)

    # Compare that second pass printed out the same mnemonic once again
    assert mnemonic == expected_mnemonic

    # start backup again - should fail
    ret = client.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_skip_backup_break(client):
    ret = client.call_raw(
        messages.ResetDevice(
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            language="en-US",
            label="test",
            skip_backup=True,
        )
    )

    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    ret = client.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))
    assert isinstance(ret, messages.Success)

    # Check if device is properly initialized
    ret = client.call_raw(messages.Initialize())
    assert ret.initialized is True
    assert ret.needs_backup is True
    assert ret.unfinished_backup is False
    assert ret.no_backup is False

    # start Backup workflow
    ret = client.call_raw(messages.BackupDevice())

    # send Initialize -> break workflow
    ret = client.call_raw(messages.Initialize())
    assert isinstance(ret, messages.Features)
    assert ret.initialized is True
    assert ret.needs_backup is False
    assert ret.unfinished_backup is True
    assert ret.no_backup is False

    # start backup again - should fail
    ret = client.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)

    # read Features again
    ret = client.call_raw(messages.Initialize())
    assert isinstance(ret, messages.Features)
    assert ret.initialized is True
    assert ret.needs_backup is False
    assert ret.unfinished_backup is True
    assert ret.no_backup is False


def test_initialized_device_backup_fail(client):
    ret = client.call_raw(messages.BackupDevice())
    assert isinstance(ret, messages.Failure)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_skip_backup_show_entropy_fail(client):
    ret = client.call_raw(
        messages.ResetDevice(
            display_random=True,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            language="en-US",
            label="test",
            skip_backup=True,
        )
    )
    assert isinstance(ret, messages.Failure)
