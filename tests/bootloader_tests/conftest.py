# This file is part of the Trezor project.
#
# Copyright (C) 2012-2026 SatoshiLabs and contributors
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

"""Bootloader emulator tests.

Every test owns its emulator runs: it starts the bootloader with explicit
startup parameters, drives it, and reads how the run ended. The emulator
binary comes from ``TREZOR_BOOTLOADER_EMU`` or the latest ``xtask`` build.

With ``--ui`` the screens are recorded from the first frame of every run
(``-r``) and hashed with the usual UI-test machinery; a test that runs the
emulator more than once gets all its runs in one recording.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import typing as t
from pathlib import Path

import pytest
import xdist

from trezorlib._internal.bootloader_emulator import (
    BootloaderEmulator,
    BootloaderStartup,
    ExitRecord,
    find_bootloader_emulator,
)

from .. import ui_tests
from ..emulators import _get_port, delete_profile, get_logfile
from ..ui_tests.common import TestCase

LOG = logging.getLogger(__name__)


def _get_worker_id(request: pytest.FixtureRequest) -> int:
    worker_id = xdist.get_xdist_worker_id(request)
    if worker_id == "master":
        return 0
    assert worker_id.startswith("gw")
    return 1 + int(worker_id[2:])


def _executable() -> Path:
    path = os.environ.get("TREZOR_BOOTLOADER_EMU")
    if path:
        return Path(path)
    return find_bootloader_emulator()


class BootloaderRunner:
    """Starts bootloader emulator runs for one test and collects their exits."""

    def __init__(
        self,
        request: pytest.FixtureRequest,
        executable: Path,
        port: int,
        profile_dir: Path,
        logfile: Path | None,
    ) -> None:
        self.request = request
        self.executable = executable
        self.port = port
        self.profile_dir = profile_dir
        self.logfile = logfile
        self.emulator: BootloaderEmulator | None = None
        self.exits: list[ExitRecord] = []
        self._runs = 0
        self._testcase: TestCase | None = None
        self._record_dir: Path | None = None

    @property
    def recording(self) -> bool:
        return bool(self.request.config.getoption("ui"))

    def _prepare_recording(self, emu: BootloaderEmulator) -> Path:
        # TestCase needs the model and language, which only a running
        # emulator reports; take them from a throwaway properties query.
        model = emu.properties()["model"]
        name, group = ui_tests.common._get_test_name_and_group(self.request.node.nodeid)
        self._testcase = TestCase(model=model, group=group, name=name, language="en")
        self._testcase.dir.mkdir(exist_ok=True, parents=True)
        shutil.rmtree(self._testcase.actual_dir, ignore_errors=True)
        self._testcase.actual_dir.mkdir()
        return self._testcase.actual_dir

    def start(self, startup: BootloaderStartup | None = None) -> BootloaderEmulator:
        """Start a run; a previous run of this test must have ended first."""
        if self.emulator is not None and self.emulator.process is not None:
            raise RuntimeError(
                "the previous run is still running; wait_exit() or stop() it"
            )
        startup = startup or BootloaderStartup()
        emu = BootloaderEmulator(
            self.executable,
            self.profile_dir,
            startup=startup,
            port=self.port,
            logfile=self.logfile,
        )
        if self.recording:
            if self._record_dir is None:
                self._record_dir = self._prepare_recording(emu)
            startup.record_dir = self._record_dir
        emu.start()
        self.emulator = emu
        return emu

    def wait_exit(self, timeout: float | None = 60) -> ExitRecord:
        """Wait for the current run to end and record how."""
        assert self.emulator is not None, "no run started"
        record = self.emulator.wait_exit(timeout)
        self.exits.append(record)
        self._finish_run()
        return record

    def abort(self) -> ExitRecord:
        """Stop a run that will not end on its own and record its state."""
        assert self.emulator is not None, "no run started"
        record = self.emulator.abort()
        self.exits.append(record)
        self._finish_run()
        return record

    def _finish_run(self) -> None:
        # Every run records its frames with the prefix of a first refresh;
        # give each run its own index so the frames sort in run order.
        if self._record_dir is not None and self._runs > 0:
            for png in self._record_dir.glob("refresh00-*.png"):
                png.rename(
                    png.with_name(
                        f"refresh{self._runs:02d}-" + png.name[len("refresh00-") :]
                    )
                )
        self._runs += 1

    def close(self) -> None:
        if self.emulator is not None and self.emulator.process is not None:
            self.emulator.stop()
            self._finish_run()
        self.emulator = None
        if self._testcase is not None:
            ui_tests.record_result(self._testcase, self.request)


@pytest.fixture
def bootloader(request: pytest.FixtureRequest) -> t.Iterator[BootloaderRunner]:
    worker_id = _get_worker_id(request)
    executable = _executable()
    logfile = get_logfile(f"trezor-bootloader-{worker_id}.log")
    with tempfile.TemporaryDirectory(
        prefix="trezor-bootloader-", delete=delete_profile()
    ) as profile_dir:
        runner = BootloaderRunner(
            request, executable, _get_port(worker_id), Path(profile_dir), logfile
        )
        try:
            yield runner
        finally:
            runner.close()
