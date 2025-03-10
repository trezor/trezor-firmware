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

from ..common import EXTERNAL_ENTROPY, MOCK_GET_ENTROPY, generate_entropy
from . import reset

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@pytest.mark.parametrize(
    "num_of_shares, threshold",
    [
        pytest.param(1, 1, id="1of1"),
        pytest.param(16, 16, id="16of16"),
    ],
)
@pytest.mark.setup_client(uninitialized=True)
def test_reset_slip39_basic(
    device_handler: "BackgroundDeviceHandler", num_of_shares: int, threshold: int
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
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

    # confirm back up
    # TODO: check also for ["backup__it_should_be_backed_up", "backup__it_should_be_backed_up_now"]
    # TR.assert_in_multiple(
    #     debug.read_layout().text_content(),
    #     ["backup__new_wallet_created", "backup__new_wallet_successfully_created"],
    # )
    reset.confirm_read(debug)

    # confirm backup intro
    # TR.assert_in(debug.read_layout().text_content(), "backup__info_multi_share_backup")
    reset.confirm_read(debug)

    # confirm checklist
    # TR.assert_in(
    #     debug.read_layout().text_content(), "reset__slip39_checklist_num_shares"
    # )
    reset.confirm_read(debug)

    # set num of shares - default is 5
    reset.set_selection(debug, num_of_shares - 5)

    # confirm checklist
    # TR.assert_in(
    #     debug.read_layout().text_content(), "reset__slip39_checklist_set_threshold"
    # )
    reset.confirm_read(debug)

    # set threshold
    # TODO: could make it general as well
    if num_of_shares == 1 and threshold == 1:
        reset.set_selection(debug, 0)
    elif num_of_shares == 16 and threshold == 16:
        # set threshold - dialog starts at 9
        reset.set_selection(debug, 7)
    else:
        raise RuntimeError("not a supported combination")

    # confirm checklist
    # TR.assert_in_multiple(
    #     debug.read_layout().text_content(),
    #     [
    #         "reset__slip39_checklist_write_down",
    #         "reset__slip39_checklist_write_down_recovery",
    #     ],
    # )
    reset.confirm_read(debug)

    # confirm backup warning
    # TR.assert_in(debug.read_layout().text_content(), "reset__never_make_digital_copy")
    reset.confirm_read(debug, middle_r=True)

    all_words: list[str] = []
    for _ in range(num_of_shares):
        # read words
        words = reset.read_words(debug)

        # confirm words
        reset.confirm_words(debug, words)

        # confirm share checked
        reset.confirm_read(debug)

        all_words.append(" ".join(words))

    # confirm backup done
    reset.confirm_read(debug)

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    reset.validate_mnemonics(all_words, secret)

    # retrieve the result to check that it's not a TrezorFailure exception
    device_handler.result()

    features = device_handler.features()
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
