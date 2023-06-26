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


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize(
    "group_count, group_threshold, share_count, share_threshold",
    [
        pytest.param(2, 2, 2, 2, id="2of2"),
        pytest.param(16, 16, 16, 16, id="16of16", marks=pytest.mark.slow),
    ],
)
@WITH_MOCK_URANDOM
def test_reset_slip39_advanced(
    device_handler: "BackgroundDeviceHandler",
    group_count: int,
    group_threshold: int,
    share_count: int,
    share_threshold: int,
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        backup_type=messages.BackupType.Slip39_Advanced,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # confirm back up
    reset.confirm_read(debug, "Success")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set num of groups - default is 5
    if group_count < 5:
        reset.set_selection(debug, buttons.RESET_MINUS, 5 - group_count)
    else:
        reset.set_selection(debug, buttons.RESET_PLUS, group_count - 5)

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set group threshold
    # TODO: could make it general as well
    if group_count == 2 and group_threshold == 2:
        reset.set_selection(debug, buttons.RESET_PLUS, 0)
    elif group_count == 16 and group_threshold == 16:
        reset.set_selection(debug, buttons.RESET_PLUS, 11)
    else:
        raise RuntimeError("not a supported combination")

    # confirm checklist
    reset.confirm_read(debug, "Checklist")

    # set share num and threshold for groups
    for _ in range(group_count):
        # set num of shares - default is 5
        if share_count < 5:
            reset.set_selection(debug, buttons.RESET_MINUS, 5 - share_count)
        else:
            reset.set_selection(debug, buttons.RESET_PLUS, share_count - 5)

        # set share threshold
        # TODO: could make it general as well
        if share_count == 2 and share_threshold == 2:
            reset.set_selection(debug, buttons.RESET_PLUS, 0)
        elif share_count == 16 and share_threshold == 16:
            reset.set_selection(debug, buttons.RESET_PLUS, 11)
        else:
            raise RuntimeError("not a supported combination")

    # confirm backup warning
    reset.confirm_read(debug, "Caution", middle_r=True)

    all_words: list[str] = []
    for _ in range(group_count):
        for _ in range(share_count):
            # read words
            words = reset.read_words(
                debug, messages.BackupType.Slip39_Advanced, do_htc=False
            )

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
    assert features.backup_type is messages.BackupType.Slip39_Advanced
