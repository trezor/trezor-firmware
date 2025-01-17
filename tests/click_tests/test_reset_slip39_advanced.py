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
from ..common import EXTERNAL_ENTROPY, MOCK_GET_ENTROPY, generate_entropy
from . import reset

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize(
    "group_count, group_threshold, share_count, share_threshold",
    [
        pytest.param(2, 2, 2, 2, id="2of2"),
        pytest.param(16, 16, 16, 16, id="16of16", marks=pytest.mark.slow),
    ],
)
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
        device.setup,
        backup_type=messages.BackupType.Slip39_Advanced,
        pin_protection=False,
        passphrase_protection=False,
        entropy_check_count=0,
        _get_entropy=MOCK_GET_ENTROPY,
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
    # TR.assert_in(debug.read_layout().text_content(), "backup__info_multi_share_backup")
    reset.confirm_read(debug)

    # confirm checklist
    # TR.assert_in(
    #     debug.read_layout().text_content(), "reset__slip39_checklist_num_groups"
    # )
    reset.confirm_read(debug)

    # set num of groups - default is 5
    assert debug.model is not None
    model_name: str = debug.model.internal_name
    if group_count < 5:
        reset.set_selection(debug, buttons.reset_minus(model_name), 5 - group_count)
    else:
        reset.set_selection(debug, buttons.reset_plus(model_name), group_count - 5)

    # confirm checklist
    # TR.assert_in_multiple(
    #     debug.read_layout().text_content(),
    #     [
    #         "reset__slip39_checklist_set_threshold",  # basic
    #         "reset__slip39_checklist_set_num_shares",  # advanced (UI bolt and delizia)
    #         "reset__slip39_checklist_num_shares",  # advanced (UI caesar)
    #     ],
    # )
    reset.confirm_read(debug)

    # set group threshold
    # TODO: could make it general as well
    if group_count == 2 and group_threshold == 2:
        reset.set_selection(debug, buttons.reset_plus(model_name), 0)
    elif group_count == 16 and group_threshold == 16:
        reset.set_selection(debug, buttons.reset_plus(model_name), 11)
    else:
        raise RuntimeError("not a supported combination")

    # confirm checklist
    # TR.assert_in_multiple(
    #     debug.read_layout().text_content(),
    #     [
    #         "reset__slip39_checklist_set_sizes",
    #         "reset__slip39_checklist_set_sizes_longer",
    #     ],
    # )
    reset.confirm_read(debug)

    # set share num and threshold for groups
    for _ in range(group_count):
        # set num of shares - default is 5
        if share_count < 5:
            reset.set_selection(debug, buttons.reset_minus(model_name), 5 - share_count)
        else:
            reset.set_selection(debug, buttons.reset_plus(model_name), share_count - 5)

        # set share threshold
        # TODO: could make it general as well
        if share_count == 2 and share_threshold == 2:
            reset.set_selection(debug, buttons.reset_plus(model_name), 0)
        elif share_count == 16 and share_threshold == 16:
            reset.set_selection(debug, buttons.reset_plus(model_name), 11)
        else:
            raise RuntimeError("not a supported combination")

    # confirm backup warning
    # TR.assert_in(debug.read_layout().text_content(), "reset__never_make_digital_copy")
    reset.confirm_read(debug, middle_r=True)

    all_words: list[str] = []
    for _ in range(group_count):
        for _ in range(share_count):
            # read words
            words = reset.read_words(debug, do_htc=False)

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
    assert features.backup_type is messages.BackupType.Slip39_Advanced_Extendable
