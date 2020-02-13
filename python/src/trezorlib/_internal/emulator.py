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

import logging
import os
import subprocess
import time
from pathlib import Path

from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.transport.udp import UdpTransport

LOG = logging.getLogger(__name__)

EMULATOR_WAIT_TIME = 60


def _rm_f(path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


class Emulator:
    STORAGE_FILENAME = None

    def __init__(
        self,
        executable,
        profile_dir,
        *,
        logfile=None,
        storage=None,
        headless=False,
        debug=True,
        extra_args=()
    ):
        self.executable = Path(executable).resolve()
        if not executable.exists():
            raise ValueError(
                "emulator executable not found: {}".format(self.executable)
            )

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

        self.client = None
        self.process = None

        self.port = 21324
        self.headless = headless
        self.debug = debug
        self.extra_args = list(extra_args)

    def make_args(self):
        return []

    def make_env(self):
        return os.environ.copy()

    def _get_transport(self):
        return UdpTransport("127.0.0.1:{}".format(self.port))

    def wait_until_ready(self, timeout=EMULATOR_WAIT_TIME):
        transport = self._get_transport()
        transport.open()
        LOG.info("Waiting for emulator to come up...")
        start = time.monotonic()
        try:
            while True:
                if transport._ping():
                    break
                if self.process.poll() is not None:
                    raise RuntimeError("Emulator proces died")

                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise TimeoutError("Can't connect to emulator")

                time.sleep(0.1)
        finally:
            transport.close()

        LOG.info("Emulator ready after {:.3f} seconds".format(time.monotonic() - start))

    def wait(self, timeout=None):
        ret = self.process.wait(timeout=timeout)
        self.process = None
        self.stop()
        return ret

    def launch_process(self):
        args = self.make_args()
        env = self.make_env()

        if hasattr(self.logfile, "write"):
            output = self.logfile
        else:
            output = open(self.logfile, "w")

        return subprocess.Popen(
            [self.executable] + args + self.extra_args,
            cwd=self.workdir,
            stdout=output,
            stderr=subprocess.STDOUT,
            env=env,
        )

    def start(self):
        if self.process:
            if self.process.poll() is not None:
                # process has died, stop and start again
                LOG.info("Starting from a stopped process.")
                self.stop()
            else:
                # process is running, no need to start again
                return

        self.process = self.launch_process()
        try:
            self.wait_until_ready()
        except TimeoutError:
            # Assuming that after the default 60-second timeout, the process is stuck
            LOG.warning(
                "Emulator did not come up after {} seconds".format(EMULATOR_WAIT_TIME)
            )
            self.process.kill()
            raise

        (self.profile_dir / "trezor.pid").write_text(str(self.process.pid) + "\n")
        (self.profile_dir / "trezor.port").write_text(str(self.port) + "\n")

        transport = self._get_transport()
        self.client = TrezorClientDebugLink(transport, auto_interact=self.debug)

        self.client.open()

    def stop(self):
        if self.client:
            self.client.close()
        self.client = None

        if self.process:
            LOG.info("Terminating emulator...")
            start = time.monotonic()
            self.process.terminate()
            try:
                self.process.wait(EMULATOR_WAIT_TIME)
                end = time.monotonic()
                LOG.info("Emulator shut down after {:.3f} seconds".format(end - start))
            except subprocess.TimeoutExpired:
                LOG.info("Emulator seems stuck. Sending kill signal.")
                self.process.kill()

        _rm_f(self.profile_dir / "trezor.pid")
        _rm_f(self.profile_dir / "trezor.port")
        self.process = None

    def restart(self):
        self.stop()
        self.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def get_storage(self):
        return self.storage.read_bytes()


class CoreEmulator(Emulator):
    STORAGE_FILENAME = "trezor.flash"

    def __init__(
        self,
        *args,
        port=None,
        main_args=("-m", "main"),
        workdir=None,
        sdcard=None,
        disable_animation=True,
        heap_size="20M",
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if workdir is not None:
            self.workdir = Path(workdir).resolve()

        self.sdcard = self.profile_dir / "trezor.sdcard"
        if sdcard is not None:
            self.sdcard.write_bytes(sdcard)

        if port:
            self.port = port
        self.disable_animation = disable_animation
        self.main_args = list(main_args)
        self.heap_size = heap_size

    def make_env(self):
        env = super().make_env()
        env.update(
            TREZOR_PROFILE_DIR=str(self.profile_dir),
            TREZOR_PROFILE=str(self.profile_dir),
            TREZOR_UDP_PORT=str(self.port),
        )
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        if self.disable_animation:
            env["TREZOR_DISABLE_FADE"] = "1"
            env["TREZOR_DISABLE_ANIMATION"] = "1"

        return env

    def make_args(self):
        pyopt = "-O0" if self.debug else "-O1"
        return (
            [pyopt, "-X", "heapsize={}".format(self.heap_size)]
            + self.main_args
            + self.extra_args
        )


class LegacyEmulator(Emulator):
    STORAGE_FILENAME = "emulator.img"

    def make_env(self):
        env = super().make_env()
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        return env
