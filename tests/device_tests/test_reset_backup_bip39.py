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

from unittest import mock

import pytest
from mnemonic import Mnemonic

from trezorlib import device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B

from ..common import click_through, generate_entropy, read_and_confirm_mnemonic

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
OS_URANDOM = mock.Mock(return_value=EXTERNAL_ENTROPY)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_msg(client):

    with mock.patch("os.urandom", OS_URANDOM), client:
        device.reset(
            client,
            display_random=False,
            strength=128,
            skip_backup=True,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="english",
            backup_type=BackupType.Bip39,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Bip39

    mnemonic = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Bip39

    assert mnemonic is not None

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_manual(client):
    def reset_skip_input_flow():
        yield  # Confirm Recovery
        client.debug.press_yes()

        yield  # Skip Backup
        client.debug.press_no()

        yield  # Confirm skip backup
        client.debug.press_no()

    with mock.patch("os.urandom", OS_URANDOM), client:
        client.set_input_flow(reset_skip_input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.reset(
            client,
            pin_protection=False,
            passphrase_protection=False,
            backup_type=BackupType.Bip39,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Bip39

    mnemonic = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Bip39

    assert mnemonic is not None

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic


def backup_flow(client):
    mnemonic = None

    def input_flow():
        nonlocal mnemonic

        # 1. Confirm Reset
        yield from click_through(client.debug, screens=1, code=B.ResetDevice)

        # mnemonic phrases
        btn_code = yield
        assert btn_code == B.ResetDevice
        mnemonic = read_and_confirm_mnemonic(client.debug, words=12)

        # confirm recovery seed check
        btn_code = yield
        assert btn_code == B.Success
        client.debug.press_yes()

        # confirm success
        btn_code = yield
        assert btn_code == B.Success
        client.debug.press_yes()

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
            ]
        )
        client.set_input_flow(input_flow)
        device.backup(client)

    return mnemonic
