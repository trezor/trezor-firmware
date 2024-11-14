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

from .. import translations as TR
from ..common import WITH_MOCK_URANDOM
from . import reset
from .common import go_next

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


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
    # TR.assert_in_multiple(
    #     debug.read_layout().text_content(),
    #     ["backup__it_should_be_backed_up", "backup__it_should_be_backed_up_now"],
    # )
    reset.confirm_read(debug)

    # confirm backup intro
    # parametrized string
    assert TR.regexp("backup__info_single_share_backup").match(
        debug.read_layout().text_content()
    )
    reset.confirm_read(debug)

    # confirm backup warning
    assert TR.reset__never_make_digital_copy in debug.read_layout().text_content()
    reset.confirm_read(debug, middle_r=True)

    # read words
    words = reset.read_words(debug)

    # confirm words
    reset.confirm_words(debug, words)

    # confirm backup done
    reset.confirm_read(debug)

    # Your backup is done
    go_next(debug)

    # TODO: some validation of the generated secret?

    assert device_handler.result() == "Initialized"
    features = device_handler.features()
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Bip39
