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

from trezorlib import btc, device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B
from trezorlib.tools import parse_path

from ..common import EXTERNAL_ENTROPY, click_through, read_and_confirm_mnemonic


@pytest.mark.skip_t1
@pytest.mark.skip_ui
@pytest.mark.setup_client(uninitialized=True)
def test_reset_recovery(client):
    mnemonic = reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))

    device.wipe(client)
    recover(client, mnemonic)
    address_after = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
    assert address_before == address_after


def reset(client, strength=128, skip_backup=False):
    mnemonic = None
    word_count = strength // 32 * 3

    def input_flow():
        nonlocal mnemonic

        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(client.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases
        btn_code = yield
        assert btn_code == B.ResetDevice
        mnemonic = read_and_confirm_mnemonic(client.debug, words=word_count)

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
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
                messages.Features(),
            ]
        )
        client.set_input_flow(input_flow)

        os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
        with mock.patch("os.urandom", os_urandom), client:
            # No PIN, no passphrase, don't display random
            device.reset(
                client,
                display_random=False,
                strength=strength,
                passphrase_protection=False,
                pin_protection=False,
                label="test",
                language="en-US",
                backup_type=BackupType.Bip39,
            )

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    return mnemonic


def recover(client, mnemonic):
    debug = client.debug
    words = mnemonic.split(" ")

    def input_flow():
        yield  # Confirm recovery
        debug.press_yes()
        yield  # Homescreen
        debug.press_yes()

        yield  # Enter word count
        debug.input(str(len(words)))

        yield  # Homescreen
        debug.press_yes()
        yield  # Enter words
        for word in words:
            debug.input(word)

        yield  # confirm success
        debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ProtectCall),
                messages.ButtonRequest(code=B.RecoveryHomepage),
                messages.ButtonRequest(code=B.MnemonicWordCount),
                messages.ButtonRequest(code=B.RecoveryHomepage),
                messages.ButtonRequest(code=B.MnemonicInput),
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
                messages.Features(),
            ]
        )
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
