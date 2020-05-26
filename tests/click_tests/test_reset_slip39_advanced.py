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

from trezorlib import device, messages

from .. import buttons
from ..common import generate_entropy
from . import reset

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2

with_mock_urandom = mock.patch("os.urandom", mock.Mock(return_value=EXTERNAL_ENTROPY))


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
@with_mock_urandom
def test_reset_slip39_advanced_2of2groups_2of2shares(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        backup_type=messages.BackupType.Slip39_Advanced,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_wait(debug, "Create new wallet")

    # confirm back up
    reset.confirm_read(debug, "Success")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set num of groups
    reset.set_selection(debug, buttons.RESET_MINUS, 3)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set group threshold
    reset.set_selection(debug, buttons.RESET_MINUS, 0)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set share num and threshold for groups
    for _ in range(2):
        # set num of shares
        reset.set_selection(debug, buttons.RESET_MINUS, 3)

        # set share threshold
        reset.set_selection(debug, buttons.RESET_MINUS, 0)

    # confirm backup warning
    reset.confirm_read(debug, "Caution")

    all_words = []
    for _ in range(2):
        for _ in range(2):
            # read words
            words = reset.read_words(debug, True)

            # confirm words
            reset.confirm_words(debug, words)

            # confirm share checked
            reset.confirm_read(debug, "Success")

            all_words.append(" ".join(words))

    # confirm backup done
    reset.confirm_read(debug, "Success")

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    reset.validate_mnemonics(all_words, secret)

    assert device_handler.result() == "Initialized"

    features = device_handler.features()
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Slip39_Advanced


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.slow
@with_mock_urandom
def test_reset_slip39_advanced_16of16groups_16of16shares(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        backup_type=messages.BackupType.Slip39_Advanced,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_wait(debug, "Create new wallet")

    # confirm back up
    reset.confirm_read(debug, "Success")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set num of groups
    reset.set_selection(debug, buttons.RESET_PLUS, 11)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set group threshold
    reset.set_selection(debug, buttons.RESET_PLUS, 11)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set share num and threshold for groups
    for _ in range(16):
        # set num of shares
        reset.set_selection(debug, buttons.RESET_PLUS, 11)

        # set share threshold
        reset.set_selection(debug, buttons.RESET_PLUS, 11)

    # confirm backup warning
    reset.confirm_read(debug, "Caution")

    all_words = []
    for _ in range(16):
        for _ in range(16):
            # read words
            words = reset.read_words(debug, True)

            # confirm words
            reset.confirm_words(debug, words)

            # confirm share checked
            reset.confirm_read(debug, "Success")

            all_words.append(" ".join(words))

    # confirm backup done
    reset.confirm_read(debug, "Success")

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    reset.validate_mnemonics(all_words, secret)

    assert device_handler.result() == "Initialized"

    features = device_handler.features()
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Slip39_Advanced
