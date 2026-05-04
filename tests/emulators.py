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

import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, Sequence, Tuple

from trezorlib._internal.emulator import (
    CoreEmulator,
    Emulator,
    LegacyEmulator,
    TropicModel,
)
from trezorlib.models import CORE_MODELS, LEGACY_MODELS

ROOT = Path(__file__).resolve().parent.parent
BINDIR = ROOT / "tests" / "emulators"

_SHARED_TROPIC_MODELS: Dict[str, TropicModel] = {}

LOCAL_BUILD_PATHS = {
    "core": ROOT / "core" / "build" / "unix" / "trezor-emu-core",
    "legacy": ROOT / "legacy" / "firmware" / "trezor.elf",
}

CORE_SRC_DIR = ROOT / "core" / "src"

ENV = {"SDL_VIDEODRIVER": "dummy"}

TROPIC_MODEL_CONFIGFILE_OLD = ROOT / "tests" / "tropic_model" / "config_old.yml"
TROPIC_MODEL_CONFIGFILE = ROOT / "tests" / "tropic_model" / "config.yml"
TROPIC_CAPABLE_MODELS = {"T3W1"}
TROPIC_OLD_CONFIG_UNTIL_VERSION = (2, 11, 1)  # inclusive


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


def _get_shared_tropic_model(
    profile_dir: str,
    workdir: Path | None,
    port: int,
    configfile: Path,
    logfile: Path | None,
) -> TropicModel:
    model = _SHARED_TROPIC_MODELS.get(profile_dir)
    if model is None or model.process is None or model.process.poll() is not None:
        if model is not None:
            model.stop()
        model = TropicModel(
            workdir=workdir or ROOT,
            profile_dir=Path(profile_dir),
            port=port,
            configfile=str(configfile),
            logfile=logfile or (Path(profile_dir) / "trezor-tropic-model.log"),
        )
        model.start()
        _SHARED_TROPIC_MODELS[profile_dir] = model
    return model


def stop_shared_tropic_model(profile_dir: str) -> None:
    model = _SHARED_TROPIC_MODELS.pop(profile_dir, None)
    if model:
        model.stop()


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


def _get_tropic_model_port(worker_id: int) -> int:
    """Get a unique port for this worker process' Tropic model.

    Guarantees to be unique because each worker has a unique ID.
    """
    return 28992 + worker_id  # 28992 is the default port tvl server listens to


def _get_port(worker_id: int) -> int:
    """Get a unique port for this worker process on which it can run.

    Guarantees to be unique because each worker has a unique ID.
    #0=>20000, #1=>20003, #2=>20006, etc.
    """
    # One emulator instance occupies 3 consecutive ports:
    # 1. normal link, 2. debug link and 3. webauthn fake interface
    # 4. USB serial 5. ble-emulator-data 6. ble-emulator-events
    return 20000 + worker_id * 6


def _get_tropic_model_configfile(tag: str | None) -> Path:
    if tag is not None and tag.startswith("v"):
        tag_version = tag[1:].partition("-")[0]
        if len(tag_version.split(".")) == 3:
            version_tuple = tuple(int(i) for i in tag_version.split("."))
            if version_tuple <= TROPIC_OLD_CONFIG_UNTIL_VERSION:
                return TROPIC_MODEL_CONFIGFILE_OLD
    return TROPIC_MODEL_CONFIGFILE


class EmulatorWrapper:

    def __init__(
        self,
        model: str | None,
        tag: str | None = None,
        storage: bytes | None = None,
        profile_dir: tempfile.TemporaryDirectory | None = None,
        worker_id: int = 0,
        headless: bool = True,
        auto_interact: bool = True,
        main_args: Sequence[str] = ("-m", "main"),
        launch_tropic_model: bool | None = None,
    ) -> None:

        if model is None:
            raise ValueError("Model must be provided")

        gen = gen_from_model(model)

        if launch_tropic_model is None:
            launch_tropic_model = is_tropic_capable_model(model)

        if tag is not None:
            executable = get_emulator_path(gen, model, tag)
        else:
            executable = LOCAL_BUILD_PATHS[gen]

        if not executable.exists():
            raise ValueError(f"emulator executable not found: {executable}")

        self.profile_dir = profile_dir or tempfile.TemporaryDirectory()
        self.own_profile_dir = profile_dir is None
        if executable == LOCAL_BUILD_PATHS["core"]:
            workdir = CORE_SRC_DIR
        else:
            workdir = None

        logs_dir = os.environ.get("TREZOR_PYTEST_LOGS_DIR")
        logfile = None
        tropic_model_logfile = None
        if logs_dir:
            logfile = Path(logs_dir) / f"trezor-{worker_id}.log"
            tropic_model_logfile = (
                Path(logs_dir) / f"trezor-tropic-model-{worker_id}.log"
            )

        tropic_configfile = _get_tropic_model_configfile(tag)
        if launch_tropic_model:
            tropic_config_output = (
                Path(self.profile_dir.name) / "tropic_model_config_output.yml"
            )
            if tropic_config_output.exists():
                tropic_configfile = tropic_config_output

        use_shared_tropic_model = launch_tropic_model and not self.own_profile_dir
        launch_tropic_model_for_emulator = launch_tropic_model
        if use_shared_tropic_model:
            shared_model = _get_shared_tropic_model(
                profile_dir=self.profile_dir.name,
                workdir=workdir,
                port=_get_tropic_model_port(worker_id),
                configfile=tropic_configfile,
                logfile=(
                    tropic_model_logfile
                    if isinstance(tropic_model_logfile, Path)
                    else None
                ),
            )
            launch_tropic_model_for_emulator = False
            tropic_model_port = shared_model.port
        else:
            tropic_model_port = _get_tropic_model_port(worker_id)
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
                launch_tropic_model=launch_tropic_model_for_emulator,
                tropic_model_port=tropic_model_port,
                tropic_model_configfile=str(tropic_configfile),
                tropic_model_logfile=tropic_model_logfile,
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
        if self.own_profile_dir:
            self.profile_dir.cleanup()
