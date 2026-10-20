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

"""Run and drive the bootloader emulator in tests.

One :class:`BootloaderEmulator` is one run of the ``bootloader-emu`` binary with
explicit startup parameters. While it runs, :class:`BootloaderTestContext`
drives the screen over the debug port and talks to the bootloader over the wire
port. When it exits, :meth:`BootloaderEmulator.wait_exit` reports how: the exit
kind, the boot command it left behind, and whether storage survived.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import IntEnum
from hashlib import blake2s
from pathlib import Path

from .. import mapping, messages, models, protobuf, protocol_v1
from ..debuglink import DebugLink
from ..exceptions import TrezorFailure
from ..messages import DebugWaitType
from ..transport import Transport
from ..transport.udp import UdpTransport
from . import emulator
from .bootargs import BootArgs
from .emulator import Emulator

if t.TYPE_CHECKING:
    from ..debuglink import LayoutType

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[4]

# Same as USB_IFACE_BASE_PORT in core/embed/io/usb/usb_config.c
DEFAULT_UDP_BASE_PORT = 21324
# The debug interface is the 2nd USB interface
DEBUG_PORT_OFFSET = 1

# Written by the unix bootutils on every exit
BOOTARGS_FILENAME = "trezor.bootargs"

MT = t.TypeVar("MT", bound=protobuf.MessageType)


class ExitKind(IntEnum):
    """emulator_exit_code_t in core/embed/sys/startup/inc/sys/bootutils.h"""

    # closed by the user or a signal; no exit record written
    QUIT = 2
    # one of the reboot_* calls; the boot command says which
    REBOOT = 3
    # jumped to firmware
    JUMP = 10
    POWER_OFF = 11
    # halted after showing the RSOD
    HALT = 12


@dataclass
class BootloaderStartup:
    """Command-line parameters of one bootloader emulator run."""

    # -s: stay in the bootloader (BOOT_COMMAND_STOP_AND_WAIT)
    stay: bool = False
    # -i: preload this firmware image into the firmware area
    firmware: Path | str | None = None
    # -w: erase the firmware area first
    wipe_firmware: bool = False
    # -f: interaction-less upgrade to this image (BOOT_COMMAND_INSTALL_UPGRADE)
    upgrade: Path | str | None = None
    # -W: boot with BOOT_COMMAND_WIPE
    wipe_command: bool = False
    # -R: boot with BOOT_COMMAND_SHOW_RSOD (models with USE_BOOTARGS_RSOD only)
    rsod_command: bool = False
    # -B: boot with the command and arguments from this file
    bootargs: Path | str | None = None
    # -r: record every screen refresh as PNG into this directory
    record_dir: Path | str | None = None
    # -c / -b: device variant written to OTP
    color_variant: int | None = None
    bitcoin_only: bool | None = None
    # -l: lock the bootloader (lockable models only)
    lock_bootloader: bool = False
    # -a
    disable_animation: bool = True

    def to_args(self) -> list[str]:
        args: list[str] = []
        if self.disable_animation:
            args.append("-a")
        if self.stay:
            args.append("-s")
        if self.wipe_firmware:
            args.append("-w")
        if self.firmware is not None:
            args += ["-i", str(self.firmware)]
        if self.upgrade is not None:
            args += ["-f", str(self.upgrade)]
        if self.wipe_command:
            args.append("-W")
        if self.rsod_command:
            args.append("-R")
        if self.bootargs is not None:
            args += ["-B", str(self.bootargs)]
        if self.record_dir is not None:
            args += ["-r", str(self.record_dir)]
        if self.color_variant is not None:
            args += ["-c", str(self.color_variant)]
        if self.bitcoin_only is not None:
            args += ["-b", "1" if self.bitcoin_only else "0"]
        if self.lock_bootloader:
            args.append("-l")
        return args


@dataclass
class ExitRecord:
    """How a bootloader emulator run ended."""

    code: int
    # None when the run did not write an exit record (QUIT)
    bootargs: BootArgs | None
    # None when the storage layout is unknown
    storage_erased: bool | None

    @property
    def kind(self) -> ExitKind | None:
        try:
            return ExitKind(self.code)
        except ValueError:
            return None


class BootloaderDebugLink(DebugLink):
    """DebugLink talking to the bootloader instead of firmware."""

    def __init__(self, transport: Transport, auto_interact: bool = True) -> None:
        super().__init__(transport, auto_interact)
        # The version-based feature checks in DebugLink describe firmware
        # releases. The bootloader implements every DebugLinkGetState wait
        # type, so report a version that enables all of them.
        self.version = (99, 0, 0)
        self.input_wait_type = DebugWaitType.CURRENT_LAYOUT

    def reseed(self, value: int) -> None:
        # The bootloader UI does not depend on the RNG and does not implement
        # DebugLinkReseedRandom.
        pass


class BootloaderWire:
    """Codec-v1 channel on the bootloader's wire port.

    Exposes ``call`` and ``features`` so that ``trezorlib.firmware.update()``
    accepts it in place of a session. The bootloader polls this port only on
    host-facing screens, so a call that needs an on-screen confirmation is
    made with :meth:`call_in_background` while the test drives the screen.
    """

    def __init__(
        self, transport: Transport, features: t.Callable[[], messages.Features]
    ) -> None:
        self.transport = transport
        self.mapping = mapping.DEFAULT_MAPPING
        self._features = features
        self._pool = ThreadPoolExecutor(max_workers=1)

    @property
    def features(self) -> messages.Features:
        return self._features()

    def write(self, msg: protobuf.MessageType) -> None:
        msg_type, msg_bytes = self.mapping.encode(msg)
        protocol_v1.write(self.transport, msg_type, msg_bytes)

    def read(self, timeout: float | None = None) -> protobuf.MessageType:
        msg_type, msg_bytes = protocol_v1.read(self.transport, timeout=timeout)
        return self.mapping.decode(msg_type, msg_bytes)

    def call(
        self,
        msg: protobuf.MessageType,
        expect: type[MT] = protobuf.MessageType,
        timeout: float | None = None,
    ) -> MT:
        self.write(msg)
        result = self.read(timeout=timeout)
        if isinstance(result, messages.Failure):
            raise TrezorFailure(result)
        return expect.ensure_isinstance(result)

    def call_in_background(
        self,
        msg: protobuf.MessageType,
        expect: type[MT] = protobuf.MessageType,
        timeout: float | None = None,
    ) -> Future[MT]:
        return self._pool.submit(self.call, msg, expect, timeout)

    def close(self) -> None:
        self._pool.shutdown(wait=False)


class BootloaderTestContext:
    """Both links to a running bootloader emulator.

    Quacks enough like ``TrezorTestContext`` for the UI-test recording
    harness: ``model``, ``features``, ``debug`` and ``sync_responses``.
    """

    def __init__(
        self,
        transport: UdpTransport,
        debug_transport: Transport,
        auto_interact: bool = True,
    ) -> None:
        self.transport = transport
        self.transport.open()
        self.debug = BootloaderDebugLink(debug_transport, auto_interact)
        self.wire = BootloaderWire(transport, lambda: self.features)
        self._features: messages.Features | None = None
        self.refresh_features()

    def refresh_features(self) -> messages.Features:
        features = self.debug._call(messages.GetFeatures(), expect=messages.Features)
        if not features.language:
            # The bootloader has no translations; the UI-test harness keys
            # recordings on the language.
            features.language = "en-US"
        self._features = features
        self.debug.model = models.by_internal_name(features.internal_model)
        return features

    @property
    def features(self) -> messages.Features:
        assert self._features is not None
        return self._features

    @property
    def model(self) -> models.TrezorModel:
        assert self.debug.model is not None
        return self.debug.model

    @property
    def layout_type(self) -> LayoutType:
        return self.debug.layout_type

    def sync_responses(self) -> None:
        # The debug link is request/response and the wire channel is only
        # used explicitly, so there is nothing to drain.
        pass

    def firmware_update(
        self, data: bytes, progress_update: t.Callable[[int], t.Any] = lambda _: None
    ) -> None:
        """Upload `data` the way `trezorlib.firmware.update()` does.

        The bootloader answers FirmwareErase with the first FirmwareRequest
        only after the user confirmed on screen, if a confirmation is due.
        """
        resp = self.wire.call(messages.FirmwareErase(length=len(data)))
        while isinstance(resp, messages.FirmwareRequest):
            payload = data[resp.offset : resp.offset + resp.length]
            resp = self.wire.call(
                messages.FirmwareUpload(payload=payload, hash=blake2s(payload).digest())
            )
            progress_update(
                resp.length if isinstance(resp, messages.FirmwareRequest) else 0
            )
        messages.Success.ensure_isinstance(resp)

    def close(self) -> None:
        self.wire.close()
        self.debug.close()
        self.transport.close()


class BootloaderEmulator(Emulator):
    """One run of the bootloader emulator.

    Unlike the firmware emulator, a run is expected to end on its own: the
    bootloader reboots, powers off, jumps to firmware or halts. Use
    :meth:`wait_exit` to collect the outcome, or :meth:`stop` to abort.
    """

    STORAGE_FILENAME = "trezor.flash"

    def __init__(
        self,
        executable: Path,
        profile_dir: str | Path,
        *,
        startup: BootloaderStartup | None = None,
        port: int | None = None,
        headless: bool = True,
        fast_exit: bool = True,
        auto_interact: bool = True,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(
            executable=executable,
            profile_dir=str(profile_dir),
            headless=headless,
            debug=True,
            auto_interact=auto_interact,
            **kwargs,
        )
        self.startup = startup or BootloaderStartup()
        if port is not None:
            self.port = port
        self._ctx: BootloaderTestContext | None = None
        # skip the delays that let a human read the screen before an exit
        self.fast_exit = fast_exit
        self._properties: dict[str, t.Any] | None = None

    @property
    def debug_port(self) -> int:
        return self.port + DEBUG_PORT_OFFSET

    @property
    def bootargs_path(self) -> Path:
        return self.profile_dir / BOOTARGS_FILENAME

    @property
    def ctx(self) -> BootloaderTestContext:
        """Both links to the running bootloader."""
        if self._ctx is None:
            raise RuntimeError("Emulator not started, or its run already ended")
        return self._ctx

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def make_args(self) -> list[str]:
        return self.startup.to_args()

    def make_env(self) -> dict[str, str]:
        env = super().make_env()
        env.update(
            TREZOR_PROFILE_DIR=str(self.profile_dir),
            TREZOR_PROFILE=str(self.profile_dir),
            TREZOR_UDP_PORT=str(self.port),
        )
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        if self.fast_exit:
            env["TREZOR_EMULATOR_FAST_EXIT"] = "1"
        return env

    def _get_debug_transport(self) -> UdpTransport:
        return UdpTransport(f"127.0.0.1:{self.debug_port}")

    def _wait_until_ready(self, timeout: float = emulator.EMULATOR_WAIT_TIME) -> bool:
        """Wait for the debug port to answer.

        Returns False when the run ended first. That is a legitimate
        outcome: a boot into trusted firmware takes the bootloader no time
        at all. The wire port is not probed because it is polled only on
        host-facing screens.
        """
        assert self.process is not None, "Emulator not started"
        probe = self._get_debug_transport()
        probe.open()
        LOG.info("Waiting for bootloader emulator (debug port %d)...", self.debug_port)
        start = time.monotonic()
        try:
            while True:
                if probe.is_ready():
                    break
                if self.process.poll() is not None:
                    LOG.info(
                        "Bootloader emulator ended before answering (code %d)",
                        self.process.returncode,
                    )
                    return False
                if time.monotonic() - start >= timeout:
                    raise TimeoutError("Can't connect to bootloader emulator")
                time.sleep(0.1)
        finally:
            probe.close()
        LOG.info("Bootloader emulator ready after %.3fs", time.monotonic() - start)
        return True

    def start(self, startup: BootloaderStartup | None = None) -> None:
        if startup is not None:
            self.startup = startup
        if self.process:
            if self.process.poll() is not None:
                self.stop()
            else:
                return

        # fail early on a broken binary, and learn the flash layout before
        # the run can change the flash file
        self.properties()

        # an exit record always belongs to the run that is about to start
        emulator._rm_f(self.bootargs_path)

        self.transport = self._get_transport()
        self.process = self._launch_process()
        emulator._RUNNING_PIDS.add(self.process)
        try:
            ready = self._wait_until_ready()
        except TimeoutError:
            LOG.warning("Bootloader emulator did not come up in time")
            self.process.kill()
            raise

        if not ready:
            # the run is over; wait_exit() reports how it ended and there is
            # no client to talk to
            return

        (self.profile_dir / "trezor.pid").write_text(str(self.process.pid) + "\n")
        (self.profile_dir / "trezor.port").write_text(str(self.port) + "\n")

        self._ctx = BootloaderTestContext(
            transport=self.transport,
            debug_transport=self._get_debug_transport(),
            auto_interact=self.auto_interact,
        )

    def stop(self) -> None:
        if self._ctx is not None:
            self._ctx.close()
            self._ctx = None
        super().stop()

    def restart(self, startup: BootloaderStartup | None = None) -> None:
        self.restart_amount += 1
        prev_screenshot_dir = (
            self._ctx.debug.screenshot_recording_dir if self._ctx else None
        )
        self.stop()
        self.start(startup)
        if prev_screenshot_dir:
            self.ctx.debug.start_recording(
                prev_screenshot_dir, refresh_index=self.restart_amount
            )

    def wait_exit(self, timeout: float | None = 60) -> ExitRecord:
        """Wait for the run to end on its own and report how."""
        assert self.process is not None, "Emulator not started"
        code = self.process.wait(timeout=timeout)
        emulator._RUNNING_PIDS.discard(self.process)
        self.process = None
        if self._ctx is not None:
            self._ctx.close()
            self._ctx = None
        emulator._rm_f(self.profile_dir / "trezor.pid")
        emulator._rm_f(self.profile_dir / "trezor.port")

        bootargs = (
            BootArgs.from_file(self.bootargs_path)
            if self.bootargs_path.exists()
            else None
        )
        record = ExitRecord(code, bootargs, self.storage_erased())
        LOG.info(
            "Bootloader emulator exited: kind=%s command=%s storage_erased=%s",
            record.kind,
            bootargs.command_name if bootargs else None,
            record.storage_erased,
        )
        return record

    def abort(self) -> ExitRecord:
        """Stop a run that would not end on its own and report its state.

        Some screens wait for the user to reconnect the device and never
        exit on the emulator; the outcome is then the storage state alone.
        """
        self.stop()
        record = ExitRecord(ExitKind.QUIT, None, self.storage_erased())
        LOG.info(
            "Bootloader emulator aborted: storage_erased=%s", record.storage_erased
        )
        return record

    def properties(self) -> dict[str, t.Any]:
        """Model and flash layout, as printed by ``bootloader-emu -p``."""
        properties = self._properties
        if properties is None:
            out = subprocess.run(
                [str(self.executable), "-p"],
                cwd=self.workdir,
                env=self.make_env(),
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            properties = json.loads(out)
            self._properties = properties
        return properties

    def storage_erased(self) -> bool | None:
        """Whether both storage areas in the flash file are blank."""
        if not self.storage.exists():
            return None
        areas = self.properties().get("storage_areas")
        if not areas:
            return None
        flash = self.storage.read_bytes()
        for area in areas:
            chunk = flash[area["offset"] : area["offset"] + area["size"]]
            if chunk.strip(b"\xff"):
                return False
        return True


def find_bootloader_emulator(model: str | None = None) -> Path:
    """Locate the bootloader emulator binary built by ``xtask build bootloader -e``."""
    artifacts = ROOT / "core" / "build" / "artifacts"
    subdir = "latest" if model is None else model.upper()
    path = artifacts / subdir / "bootloader-emu"
    if path.exists():
        return path
    raise FileNotFoundError(
        f"Bootloader emulator binary not found at {path}. Build it with: "
        f"xtask build bootloader -e -p test --bootloader-devel"
        + (f" -m {model.lower()}" if model else "")
    )
