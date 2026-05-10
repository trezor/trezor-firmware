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

from trezorlib._internal.prodtest_client import Cmd, ProdtestClient

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
    Cmd.PRODTEST_UPTIME,
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

_TROPIC_COMMANDS = {
    Cmd.TROPIC_BENCHMARK,
    Cmd.TROPIC_CERTDEV_READ,
    Cmd.TROPIC_CERTDEV_WRITE,
    Cmd.TROPIC_CERTFIDO_READ,
    Cmd.TROPIC_CERTFIDO_WRITE,
    Cmd.TROPIC_CERTTROPIC_READ,
    Cmd.TROPIC_ERASE_ALL_SLOTS,
    Cmd.TROPIC_GET_ACCESS_CREDENTIAL,
    Cmd.TROPIC_GET_CHIP_ID,
    Cmd.TROPIC_GET_FIDO_MASKING_KEY,
    Cmd.TROPIC_GET_RISCV_FW_VERSION,
    Cmd.TROPIC_GET_SPECT_FW_VERSION,
    Cmd.TROPIC_HANDSHAKE,
    Cmd.TROPIC_KEYFIDO_READ,
    Cmd.TROPIC_LOCK,
    Cmd.TROPIC_LOCK_CHECK,
    Cmd.TROPIC_PAIR,
    Cmd.TROPIC_READ_CONFIGS,
    Cmd.TROPIC_READ_SENSORS,
    Cmd.TROPIC_SEND_COMMAND,
    Cmd.TROPIC_SET_SENSORS,
    Cmd.TROPIC_STRESS_INIT,
    Cmd.TROPIC_STRESS_MAC_AND_DESTROY,
    Cmd.TROPIC_STRESS_SESSION,
    Cmd.TROPIC_STRESS_TEST,
    Cmd.TROPIC_TEST_COUNTER,
    Cmd.TROPIC_TEST_MAC_AND_DESTROY,
    Cmd.TROPIC_TEST_RMEM,
    Cmd.TROPIC_TEST_RNG,
    Cmd.TROPIC_TEST_SIGN,
    Cmd.TROPIC_TESTS_CLEANUP,
    Cmd.TROPIC_UPDATE_FW,
}

# Per-model extra commands on top of _COMMON_COMMANDS.
_MODEL_EXTRA_COMMANDS: dict[str, set[str]] = {
    "t3w1": _TOUCH_COMMANDS
    | _TROPIC_COMMANDS
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


def _expected_commands(model_name: str) -> set[str]:
    """Commands ``help`` should list for the given internal model name."""
    extras = _MODEL_EXTRA_COMMANDS.get(model_name.lower(), set())
    return _COMMON_COMMANDS | extras


def test_help_lists_expected_commands(client: ProdtestClient) -> None:
    """help should list exactly the expected commands for the model."""
    expected_commands = _expected_commands(client.model.internal_name)
    available_commands = client.available_commands
    missing = expected_commands - available_commands
    unexpected = available_commands - expected_commands

    assert not missing, f"Commands missing from help output: {missing}"
    assert not unexpected, f"Unexpected commands in help output: {unexpected}"
