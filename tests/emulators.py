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
from __future__ import annotations

import logging
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Sequence, Tuple

from trezorlib._internal.emulator import CoreEmulator, Emulator, LegacyEmulator
from trezorlib.models import CORE_MODELS, LEGACY_MODELS

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BINDIR = ROOT / "tests" / "emulators"

LOCAL_BUILD_PATHS = {
    "core": ROOT / "core" / "build-xtask" / "artifacts" / "latest" / "firmware-emu",
    "legacy": ROOT / "legacy" / "firmware" / "trezor.elf",
}

CORE_SRC_DIR = ROOT / "core" / "src"

ENV = {"SDL_VIDEODRIVER": "dummy"}

TROPIC_MODEL_CONFIGFILE = ROOT / "tests" / "tropic_model" / "config.yml"
TROPIC_MODEL_CONFIGFILE_OLD = ROOT / "tests" / "tropic_model" / "config_old.yml"
TROPIC_OLD_CONFIG_UNTIL_VERSION = (2, 12, 1)  # inclusive
TROPIC_CAPABLE_MODELS = {"T3W1"}


def is_tropic_capable_model(model_internal_name: str | None) -> bool:
    return model_internal_name in TROPIC_CAPABLE_MODELS


def gen_from_model(model_internal_name: str) -> str:
    # Accept "core" and "legacy" directly for backward compatibility
    # with callers that don't know the specific model (e.g., local builds).
    if model_internal_name in ("core", "legacy"):
        return model_internal_name

    # Compare by internal_name string, not by object equality,
    # because the models module may be patched during tests
    legacy_names = {m.internal_name for m in LEGACY_MODELS}
    core_names = {m.internal_name for m in CORE_MODELS}

    if model_internal_name in legacy_names:
        return "legacy"
    if model_internal_name in core_names:
        return "core"
    raise ValueError(f"Unknown model: {model_internal_name}")


def check_version(tag: str, version_tuple: Tuple[int, int, int]) -> None:
    if tag is not None and tag.startswith("v") and len(tag.split(".")) == 3:
        version = ".".join(str(i) for i in version_tuple)
        if tag[1:] != version:
            raise RuntimeError(f"Version mismatch: tag {tag} reports version {version}")


def get_emulator_path(
    gen: str,
    model: str,
    tag: str,
) -> Path:
    expected_name = f"trezor-emu-{gen}-{model}-{tag}"
    top_level_path = BINDIR / model / expected_name
    nested_paths = sorted(
        p for p in (BINDIR / model).glob(f"*/{expected_name}") if p.is_file()
    )

    if is_tropic_capable_model(model):
        if nested_paths:
            return nested_paths[0]
        raise ValueError(
            f"tropic-capable emulator executable not found: {BINDIR / model / '*/' / expected_name}"
        )
    else:
        return top_level_path


def get_tags() -> dict[str, list[str]]:
    result = defaultdict(list)
    for model_dir in sorted(p for p in BINDIR.iterdir() if p.is_dir()):
        seen_tags = set()
        model_name = model_dir.name

        top_level_files = sorted(
            p for p in model_dir.glob("trezor-emu-*") if p.is_file()
        )
        nested_files = sorted(
            p for p in model_dir.glob("*/trezor-emu-*") if p.is_file()
        )

        if is_tropic_capable_model(model_name):
            files = nested_files
        else:
            files = [*top_level_files, *nested_files]

        for f in files:
            try:
                # example: "trezor-emu-core-T2T1-v2.0.8" or "trezor-emu-core-T2T1-v2.0.8-46ab42fw"
                _, _, _, model, tag = f.name.split("-", maxsplit=4)
            except ValueError:
                continue

            if tag in seen_tags:
                continue
            result[model].append(tag)
            seen_tags.add(tag)
    return result


ALL_TAGS = get_tags()


def get_tropic_model_port(worker_id: int) -> int:
    """Get a unique port for this worker process' shared Tropic model.

    Guarantees to be unique because each worker has a unique ID.
    """
    if worker_id == 0:
        # was not configurable before 2.9.4, use the default value for singlecore upgrade tests
        return 28992
    else:
        return 20000 + worker_id * 7 + 6


def _get_port(worker_id: int) -> int:
    """Get a unique port for this worker process on which it can run.

    Guarantees to be unique because each worker has a unique ID.
    #0=>20000, #1=>20007, #2=>20014, etc.
    """
    # One emulator instance occupies 7 consecutive ports:
    # 1. normal link, 2. debug link and 3. webauthn fake interface
    # 4. USB serial 5. ble-emulator-data 6. ble-emulator-events
    # 7. tropic model
    # See: *_PORT_OFFSET constants in core sources
    return 20000 + worker_id * 7


class EmulatorWrapper:

    def __init__(
        self,
        model: str | None,
        tag: str | None = None,
        storage: bytes | None = None,
        profile_dir: str | None = None,
        worker_id: int = 0,
        headless: bool = True,
        auto_interact: bool = True,
        main_args: Sequence[str] = ("-m", "main"),
        tropic_model_port: int | None = None,
    ) -> None:

        if model is None:
            raise ValueError("Model must be provided")

        gen = gen_from_model(model)

        if tropic_model_port is None:
            tropic_model_port = get_tropic_model_port(worker_id)

        if tag is not None:
            executable = get_emulator_path(gen, model, tag)
        else:
            executable = LOCAL_BUILD_PATHS[gen]

        if not executable.exists():
            raise ValueError(f"emulator executable not found: {executable}")

        if profile_dir:
            self.temp_dir = None
            self.profile_dir = profile_dir
        else:
            self.temp_dir = tempfile.TemporaryDirectory(
                prefix="trezor-emulator-", delete=delete_profile()
            )
            self.profile_dir = self.temp_dir.name
            LOG.debug(
                f"Emulator profile dir: {self.profile_dir} (delete: {delete_profile()})"
            )

        if executable == LOCAL_BUILD_PATHS["core"]:
            workdir = CORE_SRC_DIR
        else:
            workdir = None

        logfile = get_logfile(f"trezor-{worker_id}.log")

        if gen == "legacy":
            self.emulator = LegacyEmulator(
                executable,
                self.profile_dir,
                storage=storage,
                headless=headless,
                auto_interact=auto_interact,
                logfile=logfile,
            )
        elif gen == "core":
            self.emulator = CoreEmulator(
                executable,
                self.profile_dir,
                storage=storage,
                workdir=workdir,
                tropic_model_port=tropic_model_port,
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

    def executable_is_tropic_capable(self) -> bool:
        """Try running the binary with --emulator-properties to see if it is Tropic capable."""
        return self.emulator.properties().get("tropic", False)

    def __enter__(self) -> Emulator:
        self.emulator.start()
        return self.emulator

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.emulator.stop()
        if self.temp_dir and not delete_profile():
            self.temp_dir.cleanup()


def get_logfile(filename: str, default_dir: Path | None = None) -> Path | None:
    logs_dir = os.environ.get("TREZOR_PYTEST_LOGS_DIR") or default_dir
    if logs_dir is None:
        return None
    return Path(logs_dir) / filename


def delete_profile() -> bool:
    return os.environ.get("TREZOR_KEEP_PROFILE_DIR") != "1"
