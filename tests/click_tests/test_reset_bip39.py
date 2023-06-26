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

from typing import TYPE_CHECKING

import pytest

from trezorlib import device, messages

from ..common import WITH_MOCK_URANDOM
from . import reset
from .common import go_next

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = [pytest.mark.skip_t1]


@pytest.mark.setup_client(uninitialized=True)
@WITH_MOCK_URANDOM
def test_reset_bip39(device_handler: "BackgroundDeviceHandler"):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        strength=128,
        backup_type=messages.BackupType.Bip39,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # confirm back up
    reset.confirm_read(debug, "Success")

    # confirm backup warning
    reset.confirm_read(debug, "Caution", middle_r=True)

    # read words
    words = reset.read_words(debug, messages.BackupType.Bip39)

    # confirm words
    reset.confirm_words(debug, words)

    # confirm backup done
    reset.confirm_read(debug, "Success")

    # Your backup is done
    go_next(debug)

    # TODO: some validation of the generated secret?

    assert device_handler.result() == "Initialized"
    features = device_handler.features()
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Bip39
