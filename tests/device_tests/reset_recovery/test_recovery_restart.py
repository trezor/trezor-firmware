# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import pytest

from trezorlib import device
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType
from trezorlib.exceptions import Cancelled
from trezorlib.messages import BackupMethod, Capability, RecoveryStatus
from trezorlib.testing import translations as TR

from ...input_flows import RecoveryFlow


@pytest.mark.models("core")
@pytest.mark.setup_client(uninitialized=True)
def test_recovery_avoid_restart(session: Session, backup_method: BackupMethod):

    debug = session.debug

    def flow():
        yield from recovery.confirm_recovery()
        # the device is now in recovery mode
        expected_br_names = {
            BackupMethod.Display: ("recovery_word_count", "recovery"),
            BackupMethod.N4W1: ("backup_read",),
        }[backup_method]
        assert (yield).name in expected_br_names
        # abort current workflow, but remain in recovery
        session.cancel()

    assert session.refresh_features().recovery_status == RecoveryStatus.Nothing

    with session.test_ctx as client:
        recovery = RecoveryFlow(client)
        client.set_input_flow(flow)
        with pytest.raises(Cancelled):
            # Recovery flow will be cancelled
            device.recover(
                session,
                backup_method=backup_method,
                pin_protection=False,
            )

        # Device shows recovery homescreen
        assert session.refresh_features().recovery_status == RecoveryStatus.Recovery

        # Interact only via DebugLink
        homescreen_content = debug.read_layout().text_content()
        if Capability.N4W1 in session.features.capabilities:
            # Recovery homescreen = choose backup method:
            assert TR.backup__type_have in homescreen_content
            assert TR.backup__type_n4w1 in homescreen_content
            assert TR.backup__type_wordlist in homescreen_content
            # Move to the next layout from recovery homescreen
            buttons = debug.screen_buttons.word_check_words()
            coords = {
                BackupMethod.N4W1: buttons[0],
                BackupMethod.Display: buttons[1],
            }[backup_method]
            debug.click(coords)
        else:
            # Recovery homescreen = choose # of words
            assert homescreen_content == TR.recovery__num_of_words
            # Move to the next layout from recovery homescreen
            if session.layout_type is LayoutType.Caesar:
                debug.press_right()
            debug.input("20")

        new_content = debug.read_layout().text_content()
        assert new_content != homescreen_content

        # send GetFeatures - current layout should stay (due to AVOID_RESTARTING_FOR)
        assert session.refresh_features().recovery_status == RecoveryStatus.Recovery
        assert new_content == debug.read_layout().text_content()
