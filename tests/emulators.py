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

import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from trezorlib._internal.emulator import CoreEmulator, Emulator, LegacyEmulator

ROOT = Path(__file__).resolve().parent.parent
BINDIR = ROOT / "tests" / "emulators"

LOCAL_BUILD_PATHS = {
    "core": ROOT / "core" / "build" / "unix" / "trezor-emu-core",
    "legacy": ROOT / "legacy" / "firmware" / "trezor.elf",
}

CORE_SRC_DIR = ROOT / "core" / "src"

ENV = {"SDL_VIDEODRIVER": "dummy"}


def check_version(tag: str, version_tuple: Tuple[int, int, int]) -> None:
    if tag is not None and tag.startswith("v") and len(tag.split(".")) == 3:
        version = ".".join(str(i) for i in version_tuple)
        if tag[1:] != version:
            raise RuntimeError(f"Version mismatch: tag {tag} reports version {version}")


def filename_from_tag(gen: str, tag: str) -> Path:
    return BINDIR / f"trezor-emu-{gen}-{tag}"


def get_tags() -> Dict[str, List[str]]:
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


def _get_port(worker_id: int) -> int:
    """Get a unique port for this worker process on which it can run.

    Guarantees to be unique because each worker has a unique ID.
    #0=>20000, #1=>20003, #2=>20006, etc.
    """
    # One emulator instance occupies 3 consecutive ports:
    # 1. normal link, 2. debug link and 3. webauthn fake interface
    return 20000 + worker_id * 3


class EmulatorWrapper:
    def __init__(
        self,
        gen: str,
        tag: Optional[str] = None,
        storage: Optional[bytes] = None,
        worker_id: int = 0,
        headless: bool = True,
        auto_interact: bool = True,
        main_args: Sequence[str] = ("-m", "main"),
    ) -> None:
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

        logs_dir = os.environ.get("TREZOR_PYTEST_LOGS_DIR")
        logfile = None
        if logs_dir:
            logfile = Path(logs_dir) / f"trezor-{worker_id}.log"

        if gen == "legacy":
            self.emulator = LegacyEmulator(
                executable,
                self.profile_dir.name,
                storage=storage,
                headless=headless,
                auto_interact=auto_interact,
                logfile=logfile,
            )
        elif gen == "core":
            self.emulator = CoreEmulator(
                executable,
                self.profile_dir.name,
                storage=storage,
                workdir=workdir,
                port=_get_port(worker_id),
                headless=headless,
                auto_interact=auto_interact,
                main_args=main_args,
                logfile=logfile,
            )
        else:
            raise ValueError(
                f"Unrecognized gen - {gen} - only 'core' and 'legacy' supported"
            )

    def __enter__(self) -> Emulator:
        self.emulator.start()
        return self.emulator

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.emulator.stop()
        self.profile_dir.cleanup()
