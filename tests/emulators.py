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

import tempfile
from collections import defaultdict
from pathlib import Path

from trezorlib._internal.emulator import CoreEmulator, LegacyEmulator

ROOT = Path(__file__).parent.parent.resolve()
BINDIR = ROOT / "tests" / "emulators"

LOCAL_BUILD_PATHS = {
    "core": ROOT / "core" / "build" / "unix" / "trezor-emu-core",
    "legacy": ROOT / "legacy" / "firmware" / "trezor.elf",
}

CORE_SRC_DIR = ROOT / "core" / "src"

ENV = {"SDL_VIDEODRIVER": "dummy"}


def check_version(tag, version_tuple):
    if tag is not None and tag.startswith("v") and len(tag.split(".")) == 3:
        version = ".".join(str(i) for i in version_tuple)
        if tag[1:] != version:
            raise RuntimeError(f"Version mismatch: tag {tag} reports version {version}")


def filename_from_tag(gen, tag):
    return BINDIR / f"trezor-emu-{gen}-{tag}"


def get_tags():
    files = list(BINDIR.iterdir())
    if not files:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )

    result = defaultdict(list)
    for f in sorted(files):
        try:
            # example: "trezor-emu-core-v2.1.1" or "trezor-emu-core-v2.1.1-46ab42fw"
            _, _, gen, tag = f.name.split("-", maxsplit=3)
            result[gen].append(tag)
        except ValueError:
            pass
    return result


ALL_TAGS = get_tags()


class EmulatorWrapper:
    def __init__(self, gen, tag=None, storage=None):
        if tag is not None:
            executable = filename_from_tag(gen, tag)
        else:
            executable = LOCAL_BUILD_PATHS[gen]

        if not executable.exists():
            raise ValueError(f"emulator executable not found: {executable}")

        self.profile_dir = tempfile.TemporaryDirectory()
        if executable == LOCAL_BUILD_PATHS["core"]:
            workdir = CORE_SRC_DIR
        else:
            workdir = None

        if gen == "legacy":
            self.emulator = LegacyEmulator(
                executable,
                self.profile_dir.name,
                storage=storage,
                headless=True,
            )
        elif gen == "core":
            self.emulator = CoreEmulator(
                executable,
                self.profile_dir.name,
                storage=storage,
                workdir=workdir,
                headless=True,
            )

    def __enter__(self):
        self.emulator.start()
        return self.emulator

    def __exit__(self, exc_type, exc_value, traceback):
        self.emulator.stop()
        self.profile_dir.cleanup()
