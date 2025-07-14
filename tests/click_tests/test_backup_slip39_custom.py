# This file is part of the Trezor project.
#
# Copyright (C) 2012-2024 SatoshiLabs and contributors
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
from trezorlib.debuglink import LayoutType

from .. import translations as TR
from ..common import EXTERNAL_ENTROPY, MOCK_GET_ENTROPY, generate_entropy
from . import reset

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@pytest.mark.parametrize(
    "group_threshold, share_threshold, share_count",
    [
        pytest.param(1, 1, 1, id="1of1"),
        pytest.param(1, 2, 3, id="2of3"),
        pytest.param(1, 5, 5, id="5of5"),
    ],
)
@pytest.mark.setup_client(uninitialized=True)
def test_backup_slip39_custom(
    device_handler: "BackgroundDeviceHandler",
    group_threshold: int,
    share_threshold: int,
    share_count: int,
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session,
        device.setup,
        strength=128,
        backup_type=messages.BackupType.Slip39_Basic,
        pin_protection=False,
        passphrase_protection=False,
        entropy_check_count=0,
        _get_entropy=MOCK_GET_ENTROPY,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # cancel back up
    reset.cancel_backup(debug, confirm=True)

    # retrieve the result to check that it's not a TrezorFailure exception
    device_handler.result()

    device_handler.run_with_session(
        device.backup,
        group_threshold=group_threshold,
        groups=[(share_threshold, share_count)],
    )

    # confirm backup configuration
    if share_count > 1:
        assert TR.regexp("reset__create_x_of_y_multi_share_backup_template").match(
            debug.read_layout().text_content().strip()
        )
    else:
        assert TR.regexp("backup__info_single_share_backup").match(
            debug.read_layout().text_content()
        )
    reset.confirm_read(debug)

    # confirm backup intro
    assert TR.reset__never_make_digital_copy in debug.read_layout().text_content()
    reset.confirm_read(debug, middle_r=True)

    all_words: list[str] = []
    for share in range(share_count):
        # read words
        eckahrt = debug.layout_type is LayoutType.Eckhart
        confirm_instruction = not eckahrt or share == 0
        words = reset.read_words(debug, confirm_instruction=confirm_instruction)

        # confirm words
        reset.confirm_words(debug, words)

        # confirm share checked
        reset.confirm_read(debug)

        all_words.append(" ".join(words))

    # confirm backup done
    if (
        debug.layout_type in (LayoutType.Delizia, LayoutType.Eckhart)
        and share_count > 1
    ):
        reset.confirm_read(debug)
    elif debug.layout_type not in (LayoutType.Delizia, LayoutType.Eckhart):
        reset.confirm_read(debug)

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    reset.validate_mnemonics(all_words[:share_threshold], secret)

    # retrieve the result to check that it's not a TrezorFailure exception
    device_handler.result()

    features = device_handler.features()
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
