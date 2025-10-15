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

import atexit
import logging
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, TextIO, Union, cast

from ..debuglink import DebugLinkNotFound, TrezorTestContext
from ..transport import Transport
from ..transport.udp import UdpTransport

LOG = logging.getLogger(__name__)

TROPIC_MODEL_WAIT_TIME = 10
EMULATOR_WAIT_TIME = 60
_RUNNING_PIDS = set()


def _cleanup_pids() -> None:
    for process in _RUNNING_PIDS:
        process.kill()


atexit.register(_cleanup_pids)


def _rm_f(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


class TropicModel:
    def __init__(
        self,
        workdir: Path,
        profile_dir: Path,
        port: int,
        configfile: str,
        logfile: Union[TextIO, str, Path],
    ) -> None:
        self.workdir = workdir
        self.profile_dir = profile_dir
        self.port = port
        self.configfile = configfile
        self.logfile = logfile
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        self.process = self._launch_process()
        _RUNNING_PIDS.add(self.process)
        try:
            self._wait_until_ready()
        except TimeoutError:
            # Assuming that after the default, the process is stuck
            LOG.warning(
                f"Tropic model did not come up after {TROPIC_MODEL_WAIT_TIME} seconds"
            )
            self.process.kill()
            raise

    def stop(self) -> None:
        if self.process:
            LOG.info("Terminating Tropic model...")
            start = time.monotonic()
            self.process.terminate()
            try:
                self.process.wait(TROPIC_MODEL_WAIT_TIME)
                end = time.monotonic()
                LOG.info(f"Tropic model shut down after {end - start:.3f} seconds")
            except subprocess.TimeoutExpired:
                LOG.info("Tropic model seems stuck. Sending kill signal.")
                self.process.kill()
            _RUNNING_PIDS.remove(self.process)

    def _launch_process(self) -> subprocess.Popen:
        # Opening the file if it is not already opened
        if hasattr(self.logfile, "write"):
            output = self.logfile
        else:
            assert isinstance(self.logfile, (str, Path))
            output = open(self.logfile, "w")

        return subprocess.Popen(
            [
                "model_server",
                "tcp",
                "-c",
                self.configfile,
                "-p",
                str(self.port),
                "-o",
                str(self.profile_dir / "tropic_model_config_output.yml"),
            ],
            cwd=self.workdir,
            stdout=cast(TextIO, output),
            stderr=subprocess.STDOUT,
        )

    def _wait_until_ready(self, timeout: float = TROPIC_MODEL_WAIT_TIME) -> None:
        assert self.process is not None, "Tropic model not started"
        LOG.info("Waiting for Tropic model to come up...")
        start = time.monotonic()
        while True:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                    break  # if we can connect to the model, it means it is ready
            except OSError:
                pass

            if self.process.poll() is not None:
                raise RuntimeError("Tropic model process died")

            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError("Can't connect to Tropic model")

            time.sleep(0.1)

        LOG.info(f"Emulator ready after {time.monotonic() - start:.3f} seconds")


class Emulator:
    STORAGE_FILENAME: str

    def __init__(
        self,
        executable: Path,
        profile_dir: str,
        *,
        logfile: Union[TextIO, str, Path, None] = None,
        storage: Optional[bytes] = None,
        headless: bool = False,
        debug: bool = True,
        auto_interact: bool = True,
        extra_args: Iterable[str] = (),
    ) -> None:
        self.executable = Path(executable).resolve()
        if not executable.exists():
            raise ValueError(f"emulator executable not found: {self.executable}")

        self.profile_dir = Path(profile_dir).resolve()
        if not self.profile_dir.exists():
            self.profile_dir.mkdir(parents=True)
        elif not self.profile_dir.is_dir():
            raise ValueError("profile_dir is not a directory")

        self.workdir = self.profile_dir

        self.storage = self.profile_dir / self.STORAGE_FILENAME
        if storage:
            self.storage.write_bytes(storage)

        if logfile:
            self.logfile = logfile
        else:
            self.logfile = self.profile_dir / "trezor.log"

        # Using `client` property instead to assert `not None`
        self._client: TrezorTestContext | None = None
        self.process: subprocess.Popen | None = None

        self.port = 21324
        self.headless = headless
        self.debug = debug
        self.auto_interact = auto_interact
        self.extra_args = list(extra_args)

        # To save all screenshots properly in one directory between restarts
        self.restart_amount = 0

    def start_tropic_model(self) -> None:
        pass

    def stop_tropic_model(self) -> None:
        pass

    @property
    def client(self) -> TrezorTestContext:
        """So that type-checkers do not see `client` as `Optional`.

        (it is not None between `start()` and `stop()` calls)
        """
        if self._client is None:
            raise RuntimeError
        return self._client

    def make_args(self) -> List[str]:
        return []

    def make_env(self) -> Dict[str, str]:
        return os.environ.copy()

    def _get_transport(self) -> UdpTransport:
        return UdpTransport(f"127.0.0.1:{self.port}")

    def _wait_until_ready(self, timeout: float = EMULATOR_WAIT_TIME) -> None:
        assert self.process is not None, "Emulator not started"
        self.transport.open()
        LOG.info("Waiting for emulator to come up...")
        start = time.monotonic()
        try:
            while True:
                if self.transport.is_ready():
                    break
                if self.process.poll() is not None:
                    raise RuntimeError("Emulator process died")

                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise TimeoutError("Can't connect to emulator")

                time.sleep(0.1)
        finally:
            self.transport.close()

        LOG.info(f"Emulator ready after {time.monotonic() - start:.3f} seconds")

    def wait(self, timeout: Optional[float] = None) -> int:
        assert self.process is not None, "Emulator not started"
        ret = self.process.wait(timeout=timeout)
        _RUNNING_PIDS.remove(self.process)
        self.process = None
        self.stop()
        return ret

    def _launch_process(self) -> subprocess.Popen:
        args = self.make_args()
        env = self.make_env()

        # Opening the file if it is not already opened
        if hasattr(self.logfile, "write"):
            output = self.logfile
        else:
            assert isinstance(self.logfile, (str, Path))
            output = open(self.logfile, "w")

        return subprocess.Popen(
            [str(self.executable)] + args + self.extra_args,
            cwd=self.workdir,
            stdout=cast(TextIO, output),
            stderr=subprocess.STDOUT,
            env=env,
        )

    def start(
        self,
        transport: Optional[UdpTransport] = None,
        debug_transport: Optional[Transport] = None,
    ) -> None:
        if self.process:
            if self.process.poll() is not None:
                # process has died, stop and start again
                LOG.info("Starting from a stopped process.")
                self.stop()
            else:
                # process is running, no need to start again
                return

        self.start_tropic_model()

        self.transport = transport or self._get_transport()
        self.process = self._launch_process()
        _RUNNING_PIDS.add(self.process)
        try:
            self._wait_until_ready()
        except TimeoutError:
            # Assuming that after the default 60-second timeout, the process is stuck
            LOG.warning(f"Emulator did not come up after {EMULATOR_WAIT_TIME} seconds")
            self.process.kill()
            raise

        (self.profile_dir / "trezor.pid").write_text(str(self.process.pid) + "\n")
        (self.profile_dir / "trezor.port").write_text(str(self.port) + "\n")

        try:
            self._client = TrezorTestContext(
                transport=self.transport,
                auto_interact=self.auto_interact,
                debug_transport=debug_transport,
            )
        except DebugLinkNotFound as e:
            # Don't fail `start()` to allow non-debug emulator sanity test.
            LOG.warning("DebugLink not found: %s", e)

    def stop(self) -> None:
        if self._client:
            self._client.transport.close()
        self._client = None

        if self.process:
            LOG.info("Terminating emulator...")
            start = time.monotonic()
            self.process.terminate()
            try:
                self.process.wait(EMULATOR_WAIT_TIME)
                end = time.monotonic()
                LOG.info(f"Emulator shut down after {end - start:.3f} seconds")
            except subprocess.TimeoutExpired:
                LOG.info("Emulator seems stuck. Sending kill signal.")
                self.process.kill()
            _RUNNING_PIDS.remove(self.process)

        self.stop_tropic_model()

        _rm_f(self.profile_dir / "trezor.pid")
        _rm_f(self.profile_dir / "trezor.port")
        self.process = None

    def restart(self) -> None:
        # preserving the recording directory between restarts
        self.restart_amount += 1
        prev_screenshot_dir = self.client.debug.screenshot_recording_dir
        debug_transport = self.client.debug.transport
        self.stop()
        self.start(transport=self.transport, debug_transport=debug_transport)
        if prev_screenshot_dir:
            self.client.debug.start_recording(
                prev_screenshot_dir, refresh_index=self.restart_amount
            )

    def __enter__(self) -> "Emulator":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.stop()

    def get_storage(self) -> bytes:
        return self.storage.read_bytes()


class CoreEmulator(Emulator):
    STORAGE_FILENAME = "trezor.flash"

    def __init__(
        self,
        *args: Any,
        launch_tropic_model: bool = False,
        tropic_model_port: Optional[int] = None,
        tropic_model_configfile: Optional[str] = None,
        tropic_model_logfile: Union[TextIO, str, Path, None] = None,
        port: Optional[int] = None,
        main_args: Sequence[str] = ("-m", "main"),
        workdir: Optional[Path] = None,
        sdcard: Optional[bytes] = None,
        disable_animation: bool = True,
        heap_size: str = "20M",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if workdir is not None:
            self.workdir = Path(workdir).resolve()

        self.sdcard = self.profile_dir / "trezor.sdcard"
        if sdcard is not None:
            self.sdcard.write_bytes(sdcard)

        if launch_tropic_model:
            assert tropic_model_port
            assert tropic_model_configfile
            self.tropic_model = TropicModel(
                workdir=self.workdir,
                profile_dir=self.profile_dir,
                port=tropic_model_port,
                configfile=tropic_model_configfile,
                logfile=(
                    tropic_model_logfile or self.profile_dir / "trezor-tropic-model.log"
                ),
            )
        else:
            self.tropic_model = None

        if port:
            self.port = port
        self.disable_animation = disable_animation
        self.main_args = list(main_args)
        self.heap_size = heap_size

    def start_tropic_model(self) -> None:
        if self.tropic_model:
            self.tropic_model.start()

    def stop_tropic_model(self) -> None:
        if self.tropic_model:
            self.tropic_model.stop()

    def make_env(self) -> Dict[str, str]:
        env = super().make_env()
        env.update(
            TREZOR_PROFILE_DIR=str(self.profile_dir),
            TREZOR_PROFILE=str(self.profile_dir),
            TREZOR_UDP_PORT=str(self.port),
        )
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        if self.headless or self.disable_animation:
            env["TREZOR_DISABLE_FADE"] = "1"
            env["TREZOR_DISABLE_ANIMATION"] = "1"
        if self.tropic_model:
            env["TROPIC_MODEL_PORT"] = str(self.tropic_model.port)

        return env

    def make_args(self) -> List[str]:
        pyopt = "-O0" if self.debug else "-O1"
        return (
            [pyopt, "-X", f"heapsize={self.heap_size}"]
            + self.main_args
            + self.extra_args
        )


class LegacyEmulator(Emulator):
    STORAGE_FILENAME = "emulator.img"

    def make_env(self) -> Dict[str, str]:
        env = super().make_env()
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        return env

    def start_tropic_model(self) -> None:
        pass

    def stop_tropic_model(self) -> None:
        pass
