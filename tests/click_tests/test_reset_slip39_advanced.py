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

    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session,
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
    if debug.read_layout().page_count() == 1:
        assert any(
            needle in debug.read_layout().text_content()
            for needle in [
                TR.backup__it_should_be_backed_up,
                TR.backup__it_should_be_backed_up_now,
            ]
        )
    reset.confirm_read(debug)

    # confirm backup intro
    assert (
        debug.read_layout().text_content().strip() in TR.backup__info_multi_share_backup
    )
    reset.confirm_read(debug)

    # confirm checklist
    assert any(
        needle in debug.read_layout().text_content()
        for needle in [
            TR.reset__slip39_checklist_set_num_groups,
            TR.reset__slip39_checklist_num_groups,
        ]
    )
    reset.confirm_read(debug)

    # set num of groups - default is 5
    assert any(
        needle in debug.read_layout().title()
        for needle in [
            TR.reset__slip39_checklist_set_num_groups,
            TR.reset__slip39_checklist_num_groups,
            TR.reset__title_number_of_groups,
            TR.reset__title_set_number_of_groups,
        ]
    )
    reset.set_selection(debug, group_count - 5)

    # confirm checklist
    assert any(
        needle in debug.read_layout().text_content()
        for needle in [
            TR.reset__slip39_checklist_set_threshold,  # basic
            TR.reset__slip39_checklist_set_num_shares,  # advanced (UI bolt and delizia)
            TR.reset__slip39_checklist_num_shares,  # advanced (UI caesar)
        ]
    )
    reset.confirm_read(debug)

    # set group threshold
    # TODO: could make it general as well
    if group_count == 2 and group_threshold == 2:
        reset.set_selection(debug, 0)
    elif group_count == 16 and group_threshold == 16:
        reset.set_selection(debug, 11)
    else:
        raise RuntimeError("not a supported combination")

    # confirm checklist
    raw = debug.read_layout().raw_content_paragraphs()
    # TODO: make sure the page does not overflow
    if raw and raw[-1] and raw[-1][-1].strip() == "...":
        # page overflows, text_content is not complete
        pass
    else:
        assert any(
            needle in debug.read_layout().text_content()
            for needle in [
                TR.reset__slip39_checklist_set_sizes,
                TR.reset__slip39_checklist_set_sizes_longer,
            ]
        )
    reset.confirm_read(debug)

    # set share num and threshold for groups
    for _ in range(group_count):
        # set num of shares - default is 5
        reset.set_selection(debug, share_count - 5)

        # set share threshold
        # TODO: could make it general as well
        if share_count == 2 and share_threshold == 2:
            reset.set_selection(debug, 0)
        elif share_count == 16 and share_threshold == 16:
            reset.set_selection(debug, 11)
        else:
            raise RuntimeError("not a supported combination")

    # confirm backup warning
    assert TR.reset__never_make_digital_copy in debug.read_layout().text_content()
    reset.confirm_read(debug, middle_r=True)

    all_words: list[str] = []
    for _ in range(group_count):
        for _ in range(share_count):
            # In 16-of-16 scenario, skip 1500 ms HTC after each word set
            # to avoid long test durations
            is_16_of_16 = group_count == 16 and group_threshold == 16
            do_htc = not is_16_of_16
            skip_intro = is_16_of_16

            words = reset.read_words(debug, do_htc=do_htc)

            # confirm words
            reset.confirm_words(debug, words, skip_intro=skip_intro)

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
