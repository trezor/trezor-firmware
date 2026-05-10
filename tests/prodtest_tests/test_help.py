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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import pytest

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand

# Commands present on every supported model.
_COMMON_COMMANDS = {
    Cmd.BOARDLOADER_UPDATE,
    Cmd.BOARDLOADER_VERSION,
    Cmd.CRC_DISABLE,
    Cmd.CRC_ENABLE,
    Cmd.CRC_STATUS,
    Cmd.DISPLAY_BARS,
    Cmd.DISPLAY_BORDER,
    Cmd.DISPLAY_SET_BACKLIGHT,
    Cmd.DISPLAY_TEXT,
    Cmd.GET_CPUID,
    Cmd.HELP,
    Cmd.HW_REVISION,
    Cmd.LOG_FILTER,
    Cmd.MANUFACTURING_LOCK_READ,
    Cmd.OTP_BATCH_READ,
    Cmd.OTP_BATCH_WRITE,
    Cmd.OTP_DEVICE_SN_READ,
    Cmd.OTP_DEVICE_SN_WRITE,
    Cmd.OTP_VARIANT_READ,
    Cmd.OTP_VARIANT_WRITE,
    Cmd.PING,
    Cmd.PRODTEST_HOMESCREEN,
    Cmd.PRODTEST_MODEL,
    Cmd.PRODTEST_MEM_READ,
    Cmd.PRODTEST_MEM_WRITE,
    Cmd.PRODTEST_VERSION,
    Cmd.PRODTEST_WIPE,
    Cmd.REBOOT,
    Cmd.REBOOT_TO_BOOTLOADER,
    Cmd.SBU_SET,
    Cmd.SECURE_CHANNEL_HANDSHAKE_1,
    Cmd.SECURE_CHANNEL_HANDSHAKE_2,
    Cmd.TAMPER_READ,
    Cmd.UNIT_TEST_LIST,
    Cmd.UNIT_TEST_RUN,
}

_TOUCH_COMMANDS = {
    Cmd.HAPTIC_TEST,
    Cmd.TOUCH_DRAW,
    Cmd.TOUCH_TEST,
    Cmd.TOUCH_TEST_CUSTOM,
    Cmd.TOUCH_TEST_IDLE,
    Cmd.TOUCH_TEST_POWER,
    Cmd.TOUCH_TEST_SENSITIVITY,
    Cmd.TOUCH_VERSION,
}

# Per-model extra commands on top of _COMMON_COMMANDS.
_MODEL_EXTRA_COMMANDS: dict[str, set[str]] = {
    "t3b1": {
        Cmd.BUTTON_TEST,
    },
    "t3t1": _TOUCH_COMMANDS | {Cmd.SDCARD_TEST},
    "t3w1": _TOUCH_COMMANDS
    | {
        Cmd.BACKUP_RAM_ERASE,
        Cmd.BACKUP_RAM_LIST,
        Cmd.BACKUP_RAM_READ,
        Cmd.BACKUP_RAM_WRITE,
        Cmd.BUTTON_TEST,
        Cmd.MANUFACTURING_LOCK_WRITE,
        Cmd.RGBLED_EFFECT_START,
        Cmd.RGBLED_EFFECT_STOP,
        Cmd.RGBLED_SET,
        Cmd.TELEMETRY_READ,
        Cmd.TELEMETRY_RESET,
    },
}


@pytest.fixture(scope="session")
def expected_commands(prodtest_client: ProdtestClient) -> set[str]:
    model_name = prodtest_client.model.internal_name.lower()
    extras = _MODEL_EXTRA_COMMANDS.get(model_name, set())
    return _COMMON_COMMANDS | extras


def test_help_lists_expected_commands(
    prodtest_client: ProdtestClient,
    expected_commands: set[str],
) -> None:
    """help should list exactly the expected commands for the model."""
    resp = prodtest_client.command(ProdtestCommand(Cmd.HELP))
    assert resp.traces

    # Each trace line is " <name> - <info>"; extract the command name.
    listed = {
        line.split()[0]
        for line in resp.traces
        if line.strip() and not line.startswith("Available")
    }

    missing = expected_commands - listed
    unexpected = listed - expected_commands

    assert not missing, f"Commands missing from help output: {missing}"
    assert not unexpected, f"Unexpected commands in help output: {unexpected}"
