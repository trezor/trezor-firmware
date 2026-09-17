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

from trezorlib import debuglink, device
from trezorlib.messages import SafetyCheckLevel

from ..common import MNEMONIC12
from ..emulators import Emulator
from ..upgrade_tests import core_only


@core_only
@pytest.mark.parametrize(
    "set_level,after_level",
    [
        (SafetyCheckLevel.Strict, SafetyCheckLevel.Strict),
        (SafetyCheckLevel.PromptTemporarily, SafetyCheckLevel.Strict),
        (SafetyCheckLevel.PromptAlways, SafetyCheckLevel.PromptAlways),
    ],
)
def test_safety_checks_level_after_reboot(
    core_emulator: Emulator, set_level: SafetyCheckLevel, after_level: SafetyCheckLevel
):
    device.wipe(core_emulator.client.get_seedless_session())
    debuglink.load_device(
        core_emulator.client.get_seedless_session(),
        mnemonic=MNEMONIC12,
        pin="",
        passphrase_protection=False,
        label="SAFETYLEVEL",
    )

    device.apply_settings(core_emulator.client.get_session(), safety_checks=set_level)
    core_emulator.client.refresh_features()
    assert core_emulator.client.features.safety_checks == set_level

    core_emulator.restart()

    assert core_emulator.client.features.safety_checks == after_level
