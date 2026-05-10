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

from __future__ import annotations

import logging
import typing as t
import zlib
from functools import cached_property

from ..models import TrezorModel, by_internal_name

if t.TYPE_CHECKING:
    from .prodtest_transport import VcpUdpTransport

LOG = logging.getLogger(__name__)


class ResponseNotOkError(Exception):
    def __init__(self, response: ProdtestResponse | None = None, *args: t.Any) -> None:
        self.response = response
        super().__init__(*args)


class CrcMismatchError(Exception):
    pass


class Cmd:
    BACKUP_RAM_ERASE = "backup-ram-erase"
    BACKUP_RAM_LIST = "backup-ram-list"
    BACKUP_RAM_READ = "backup-ram-read"
    BACKUP_RAM_WRITE = "backup-ram-write"
    BOARDLOADER_UPDATE = "boardloader-update"
    BOARDLOADER_VERSION = "boardloader-version"
    BUTTON_TEST = "button-test"
    CRC_DISABLE = "crc-disable"
    CRC_ENABLE = "crc-enable"
    CRC_STATUS = "crc-status"
    DISPLAY_BARS = "display-bars"
    DISPLAY_BORDER = "display-border"
    DISPLAY_SET_BACKLIGHT = "display-set-backlight"
    DISPLAY_TEXT = "display-text"
    GET_CPUID = "get-cpuid"
    HAPTIC_TEST = "haptic-test"
    HELP = "help"
    HW_REVISION = "hw-revision"
    LOG_FILTER = "log-filter"
    MANUFACTURING_LOCK_READ = "manufacturing-lock-read"
    MANUFACTURING_LOCK_WRITE = "manufacturing-lock-write"
    OTP_BATCH_READ = "otp-batch-read"
    OTP_BATCH_WRITE = "otp-batch-write"
    OTP_DEVICE_SN_READ = "otp-device-sn-read"
    OTP_DEVICE_SN_WRITE = "otp-device-sn-write"
    OTP_VARIANT_READ = "otp-variant-read"
    OTP_VARIANT_WRITE = "otp-variant-write"
    PING = "ping"
    PRODTEST_HOMESCREEN = "prodtest-homescreen"
    PRODTEST_MEM_READ = "prodtest-mem-read"
    PRODTEST_MEM_WRITE = "prodtest-mem-write"
    PRODTEST_MODEL = "prodtest-model"
    PRODTEST_UPTIME = "prodtest-uptime"
    PRODTEST_VERSION = "prodtest-version"
    PRODTEST_WIPE = "prodtest-wipe"
    REBOOT = "reboot"
    REBOOT_TO_BOOTLOADER = "reboot-to-bootloader"
    RGBLED_EFFECT_START = "rgbled-effect-start"
    RGBLED_EFFECT_STOP = "rgbled-effect-stop"
    RGBLED_SET = "rgbled-set"
    SBU_SET = "sbu-set"
    SDCARD_TEST = "sdcard-test"
    SECURE_CHANNEL_HANDSHAKE_1 = "secure-channel-handshake-1"
    SECURE_CHANNEL_HANDSHAKE_2 = "secure-channel-handshake-2"
    TAMPER_READ = "tamper-read"
    TELEMETRY_READ = "telemetry-read"
    TELEMETRY_RESET = "telemetry-reset"
    TOUCH_DRAW = "touch-draw"
    TOUCH_TEST = "touch-test"
    TOUCH_TEST_CUSTOM = "touch-test-custom"
    TOUCH_TEST_IDLE = "touch-test-idle"
    TOUCH_TEST_POWER = "touch-test-power"
    TOUCH_TEST_SENSITIVITY = "touch-test-sensitivity"
    TOUCH_VERSION = "touch-version"
    TROPIC_BENCHMARK = "tropic-benchmark"
    TROPIC_CERTDEV_READ = "tropic-certdev-read"
    TROPIC_CERTDEV_WRITE = "tropic-certdev-write"
    TROPIC_CERTFIDO_READ = "tropic-certfido-read"
    TROPIC_CERTFIDO_WRITE = "tropic-certfido-write"
    TROPIC_CERTTROPIC_READ = "tropic-certtropic-read"
    TROPIC_ERASE_ALL_SLOTS = "tropic-erase-all-slots"
    TROPIC_GET_ACCESS_CREDENTIAL = "tropic-get-access-credential"
    TROPIC_GET_CHIP_ID = "tropic-get-chip-id"
    TROPIC_GET_FIDO_MASKING_KEY = "tropic-get-fido-masking-key"
    TROPIC_GET_RISCV_FW_VERSION = "tropic-get-riscv-fw-version"
    TROPIC_GET_SPECT_FW_VERSION = "tropic-get-spect-fw-version"
    TROPIC_HANDSHAKE = "tropic-handshake"
    TROPIC_KEYFIDO_READ = "tropic-keyfido-read"
    TROPIC_LOCK = "tropic-lock"
    TROPIC_LOCK_CHECK = "tropic-lock-check"
    TROPIC_PAIR = "tropic-pair"
    TROPIC_READ_CONFIGS = "tropic-read-configs"
    TROPIC_READ_SENSORS = "tropic-read-sensors"
    TROPIC_SEND_COMMAND = "tropic-send-command"
    TROPIC_SET_SENSORS = "tropic-set-sensors"
    TROPIC_STRESS_INIT = "tropic-stress-init"
    TROPIC_STRESS_MAC_AND_DESTROY = "tropic-stress-mac-and-destroy"
    TROPIC_STRESS_SESSION = "tropic-stress-session"
    TROPIC_STRESS_TEST = "tropic-stress-test"
    TROPIC_TEST_COUNTER = "tropic-test-counter"
    TROPIC_TEST_MAC_AND_DESTROY = "tropic-test-mac-and-destroy"
    TROPIC_TEST_RMEM = "tropic-test-rmem"
    TROPIC_TEST_RNG = "tropic-test-rng"
    TROPIC_TEST_SIGN = "tropic-test-sign"
    TROPIC_TESTS_CLEANUP = "tropic-tests-cleanup"
    TROPIC_UPDATE_FW = "tropic-update-fw"
    UNIT_TEST_LIST = "unit-test-list"
    UNIT_TEST_RUN = "unit-test-run"


class ProdtestCommand:
    def __init__(self, name: str, *args: str) -> None:
        self.name = name
        self._payload = " ".join((self.name, *args))

    def get(self, crc_enabled: bool = False) -> str:
        if not crc_enabled:
            return self._payload
        crc = zlib.crc32(self._payload.encode())
        return f"checked-{self._payload} {crc:08X}"


class ProdtestResponse:
    def __init__(
        self,
        is_ok: bool,
        args: str,
        progress: list[str] | None = None,
        traces: list[str] | None = None,
    ) -> None:
        self.is_ok = is_ok
        self.args = args
        self.progress = progress
        self.traces = traces

    @property
    def error_code(self) -> int:
        """Numeric error code of a failed response.

        The device's CLI formats error args as `<code> "message"`, so this is
        only meaningful when `is_ok` is False.
        """
        return int(self.args.split()[0])


class ProdtestClient:
    DEFAULT_TIMEOUT: float = 30

    def __init__(self, transport: VcpUdpTransport) -> None:
        self.transport = transport
        self.crc_enabled: bool = False

    @cached_property
    def model(self) -> TrezorModel:
        """Query and cache the model reported by the device.

        Raises ValueError if the response is not a recognised internal model name.
        """
        resp = self.command_ok(ProdtestCommand(Cmd.PRODTEST_MODEL))
        model = by_internal_name(resp.args.upper())
        if model is None:
            raise ValueError(
                f"prodtest-model returned unknown model name: {resp.args!r}"
            )
        return model

    def command(
        self, cmd: ProdtestCommand, timeout: float = DEFAULT_TIMEOUT
    ) -> ProdtestResponse:

        self.transport.writeline(cmd.get(self.crc_enabled))

        progress_lines: list[str] = []
        trace_lines: list[str] = []

        while True:
            line = self._strip_crc(self.transport.readline(timeout))
            if line.startswith("OK"):
                ok_args = line[2:].strip()
                self._update_crc_state(cmd, ok_args)
                return ProdtestResponse(
                    is_ok=True,
                    args=ok_args,
                    progress=progress_lines,
                    traces=trace_lines,
                )
            elif line.startswith("ERROR"):
                err_args = line[5:].strip()
                return ProdtestResponse(
                    is_ok=False,
                    args=err_args,
                    progress=progress_lines,
                    traces=trace_lines,
                )
            elif line.startswith("PROGRESS"):
                progress_lines.append(line[8:].strip())
            elif line.startswith("#"):
                trace_lines.append(line[1:].strip())
            else:
                LOG.warning("Unexpected line from prodtest: %s", line)

    def command_ok(
        self, cmd: ProdtestCommand, timeout: float = DEFAULT_TIMEOUT
    ) -> ProdtestResponse:
        response = self.command(cmd, timeout=timeout)
        if not response.is_ok:
            raise ResponseNotOkError(response, f"{cmd.name!r} failed: {response.args}")
        return response

    def close(self) -> None:
        self.transport.close()

    def _strip_crc(self, line: str) -> str:
        """Verify and remove the trailing CRC suffix from a response line.

        When CRC is active the device appends a space and an 8-digit hex CRC-32
        (computed over the preceding line content) to every response line. If no
        CRC is expected the line is returned unchanged.
        """
        if not self.crc_enabled:
            return line

        payload, sep, crc_str = line.rpartition(" ")
        if not sep or len(crc_str) != 8:
            raise CrcMismatchError(f"Missing CRC suffix in response: {line!r}")
        try:
            received = int(crc_str, 16)
        except ValueError:
            raise CrcMismatchError(f"Malformed CRC suffix in response: {line!r}")

        expected = zlib.crc32(payload.encode())
        if received != expected:
            raise CrcMismatchError(
                f"CRC mismatch in response {line!r}: "
                f"expected {expected:08X}, got {crc_str.upper()}"
            )
        return payload

    def _update_crc_state(self, cmd: ProdtestCommand, ok_args: str) -> None:
        """Keep crc_enabled in sync with device state."""
        if cmd.name == Cmd.CRC_ENABLE:
            self.crc_enabled = True
        elif cmd.name == Cmd.CRC_DISABLE:
            self.crc_enabled = False
        elif cmd.name == Cmd.CRC_STATUS:
            self.crc_enabled = ok_args == "1"
