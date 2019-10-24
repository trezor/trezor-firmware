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

import gzip
import os
import subprocess
import tempfile
import time
from collections import defaultdict

from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.transport.udp import UdpTransport

ROOT = os.path.abspath(os.path.dirname(__file__) + "/../..")
BINDIR = ROOT + "/tests/emulator_tests/emulators"
LOCAL_BUILD_PATHS = {
    "core": ROOT + "/core/build/unix/micropython",
    "legacy": ROOT + "/legacy/firmware/trezor.elf",
}

SD_CARD_GZ = ROOT + "/tests/trezor.sdcard.gz"

ENV = {"SDL_VIDEODRIVER": "dummy"}


def check_version(tag, version_tuple):
    if tag is not None and tag.startswith("v") and len(tag.split(".")) == 3:
        version = ".".join(str(i) for i in version_tuple)
        if tag[1:] != version:
            raise RuntimeError(f"Version mismatch: tag {tag} reports version {version}")


def filename_from_tag(gen, tag):
    return f"{BINDIR}/trezor-emu-{gen}-{tag}"


def get_tags():
    files = os.listdir(BINDIR)
    if not files:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )

    result = defaultdict(list)
    for f in sorted(files):
        try:
            # example: "trezor-emu-core-v2.1.1"
            _, _, gen, tag = f.split("-", maxsplit=3)
            result[gen].append(tag)
        except ValueError:
            pass
    return result


ALL_TAGS = get_tags()


class EmulatorWrapper:
    def __init__(self, gen, tag=None, executable=None, storage=None):
        self.gen = gen
        self.tag = tag

        if executable is not None:
            self.executable = executable
        elif tag is not None:
            self.executable = filename_from_tag(gen, tag)
        else:
            self.executable = LOCAL_BUILD_PATHS[gen]

        if not os.path.exists(self.executable):
            raise ValueError(f"emulator executable not found: {self.executable}")

        self.workdir = tempfile.TemporaryDirectory()
        if storage:
            open(self._storage_file(), "wb").write(storage)

        with gzip.open(SD_CARD_GZ, "rb") as gz:
            with open(self.workdir.name + "/trezor.sdcard", "wb") as sd:
                sd.write(gz.read())

        self.client = None

    def _get_params_core(self):
        env = ENV.copy()
        args = [self.executable, "-m", "main"]
        # for firmware 2.1.2 and newer
        env["TREZOR_PROFILE_DIR"] = self.workdir.name
        # for firmware 2.1.1 and older
        env["TREZOR_PROFILE"] = self.workdir.name

        if self.executable == LOCAL_BUILD_PATHS["core"]:
            cwd = ROOT + "/core/src"
        else:
            cwd = self.workdir.name

        return env, args, cwd

    def _get_params_legacy(self):
        env = ENV.copy()
        args = [self.executable]
        cwd = self.workdir.name
        return env, args, cwd

    def _get_params(self):
        if self.gen == "core":
            return self._get_params_core()
        elif self.gen == "legacy":
            return self._get_params_legacy()
        else:
            raise ValueError("Unknown gen")

    def start(self):
        env, args, cwd = self._get_params()
        self.process = subprocess.Popen(
            args, cwd=cwd, env=env, stdout=open(os.devnull, "w")
        )

        # wait until emulator is listening
        transport = UdpTransport("127.0.0.1:21324")
        transport.open()
        for _ in range(300):
            if transport._ping():
                break
            if self.process.poll() is not None:
                self._cleanup()
                raise RuntimeError("Emulator proces died")
            time.sleep(0.1)
        else:
            # could not connect after 300 attempts * 0.1s = 30s of waiting
            self._cleanup()
            raise RuntimeError("Can't connect to emulator")
        transport.close()

        self.client = TrezorClientDebugLink(transport)
        self.client.open()
        check_version(self.tag, self.client.version)

    def stop(self):
        if self.client:
            self.client.close()
        self.process.terminate()
        try:
            self.process.wait(1)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def restart(self):
        self.stop()
        self.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._cleanup()

    def _cleanup(self):
        self.stop()
        self.workdir.cleanup()

    def _storage_file(self):
        if self.gen == "legacy":
            return self.workdir.name + "/emulator.img"
        elif self.gen == "core":
            return self.workdir.name + "/trezor.flash"
        else:
            raise ValueError("Unknown gen")

    def storage(self):
        return open(self._storage_file(), "rb").read()
