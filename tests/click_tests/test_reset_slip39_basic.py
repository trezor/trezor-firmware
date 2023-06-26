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

from .. import buttons
from ..common import EXTERNAL_ENTROPY, WITH_MOCK_URANDOM, generate_entropy
from . import reset

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = [pytest.mark.skip_t1]


@pytest.mark.parametrize(
    "num_of_shares, threshold",
    [
        pytest.param(1, 1, id="1of1"),
        pytest.param(16, 16, id="16of16"),
    ],
)
@pytest.mark.setup_client(uninitialized=True)
@WITH_MOCK_URANDOM
def test_reset_slip39_basic(
    device_handler: "BackgroundDeviceHandler", num_of_shares: int, threshold: int
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        strength=128,
        backup_type=messages.BackupType.Slip39_Basic,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # confirm back up
    reset.confirm_read(debug, "Success")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set num of shares - default is 5
    if num_of_shares < 5:
        reset.set_selection(debug, buttons.RESET_MINUS, 5 - num_of_shares)
    else:
        reset.set_selection(debug, buttons.RESET_PLUS, num_of_shares - 5)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set threshold
    # TODO: could make it general as well
    if num_of_shares == 1 and threshold == 1:
        reset.set_selection(debug, buttons.RESET_PLUS, 0)
    elif num_of_shares == 16 and threshold == 16:
        reset.set_selection(debug, buttons.RESET_PLUS, 11)
    else:
        raise RuntimeError("not a supported combination")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # confirm backup warning
    reset.confirm_read(debug, "Caution", middle_r=True)

    all_words: list[str] = []
    for _ in range(num_of_shares):
        # read words
        words = reset.read_words(debug, messages.BackupType.Slip39_Basic)

        # confirm words
        reset.confirm_words(debug, words)

        # confirm share checked
        reset.confirm_read(debug, "Success")

        all_words.append(" ".join(words))

    # confirm backup done
    reset.confirm_read(debug, "Success")

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
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
