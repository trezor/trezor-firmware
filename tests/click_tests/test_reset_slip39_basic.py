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


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_reset_slip39_basic_1of1(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), device_handler:
        device_handler.run(
            device.reset,
            strength=128,
            backup_type=messages.BackupType.Slip39_Basic,
            pin_protection=False,
        )

        # confirm new wallet
        reset.confirm_wait(debug, "Create new wallet")

        # confirm back up
        reset.confirm_read(debug, "Success")

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # set num of shares
        # default is 5 so we press RESET_MINUS 4 times
        reset.set_selection(debug, buttons.RESET_MINUS, 4)

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # set threshold
        # threshold will default to 1
        reset.set_selection(debug, buttons.RESET_MINUS, 0)

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # confirm backup warning
        reset.confirm_read(debug, "Caution")

        # read words
        words = reset.read_words(debug)

        # confirm words
        reset.confirm_words(debug, words)

        # confirm share checked
        reset.confirm_read(debug, "Success")

        # confirm backup done
        reset.confirm_read(debug, "Success")

        # generate secret locally
        internal_entropy = debug.state().reset_entropy
        secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

        # validate that all combinations will result in the correct master secret
        validate = [" ".join(words)]
        reset.validate_mnemonics(validate, secret)

        assert device_handler.result() == "Initialized"
        features = device_handler.features()
        assert features.initialized is True
        assert features.needs_backup is False
        assert features.pin_protection is False
        assert features.passphrase_protection is False
        assert features.backup_type is messages.BackupType.Slip39_Basic


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_reset_slip39_basic_16of16(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), device_handler:
        device_handler.run(
            device.reset,
            strength=128,
            backup_type=messages.BackupType.Slip39_Basic,
            pin_protection=False,
        )

        # confirm new wallet
        reset.confirm_wait(debug, "Create new wallet")

        # confirm back up
        reset.confirm_read(debug, "Success")

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # set num of shares
        # default is 5 so we add 11
        reset.set_selection(debug, buttons.RESET_PLUS, 11)

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # set threshold
        # default is 5 so we add 11
        reset.set_selection(debug, buttons.RESET_PLUS, 11)

        # confirm checklist
        reset.confirm_read(debug, "Checklist")

        # confirm backup warning
        reset.confirm_read(debug, "Caution")

        all_words = []
        for _ in range(16):
            # read words
            words = reset.read_words(debug)

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
        assert features.backup_type is messages.BackupType.Slip39_Basic
