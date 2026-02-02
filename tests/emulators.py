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

from trezorlib._internal.emulator import CoreEmulator, Emulator, LegacyEmulator, TropicModel
from trezorlib.models import CORE_MODELS, LEGACY_MODELS, by_internal_name

ROOT = Path(__file__).resolve().parent.parent
BINDIR = ROOT / "tests" / "emulators"

_SHARED_TROPIC_MODELS: Dict[str, TropicModel] = {}

LOCAL_BUILD_PATHS = {
    "core": ROOT / "core" / "build" / "unix" / "trezor-emu-core",
    "legacy": ROOT / "legacy" / "firmware" / "trezor.elf",
}

CORE_SRC_DIR = ROOT / "core" / "src"

ENV = {"SDL_VIDEODRIVER": "dummy"}

TROPIC_MODEL_CONFIGFILE = ROOT / "tests" / "tropic_model" / "config.yml"


def gen_from_model(model_internal_name: str) -> str:
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


def get_emulator_path(gen: str, model: str, tag: str) -> Path:
    return BINDIR / model / f"trezor-emu-{gen}-{model}-{tag}"


def get_tags() -> dict[str, list[str]]:
    files = [p for p in BINDIR.glob("*/trezor-emu-*") if p.is_file()]

    result = defaultdict(list)
    for f in sorted(files):
        try:
            # example: "trezor-emu-core-T2T1-v2.0.8" or "trezor-emu-core-T2T1-v2.0.8-46ab42fw"
            _, _, _, model, tag = f.name.split("-", maxsplit=4)
            result[model].append(tag)
        except ValueError:
            pass
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


class EmulatorWrapper:

    def __init__(
        self,
        gen: str,
        tag: str | None = None,
        model: str | None = None,
        storage: bytes | None = None,
           profile_dir: tempfile.TemporaryDirectory | None = None,
        worker_id: int = 0,
        headless: bool = True,
        auto_interact: bool = True,
        main_args: Sequence[str] = ("-m", "main"),
        launch_tropic_model: bool = False,
    ) -> None:

        if tag is not None and model is not None:
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

        tropic_configfile = Path(TROPIC_MODEL_CONFIGFILE)
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
                logfile=tropic_model_logfile if isinstance(tropic_model_logfile, Path) else None,
            )
            os.environ["TROPIC_MODEL_PORT"] = str(shared_model.port)
            launch_tropic_model_for_emulator = False

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
                tropic_model_port=_get_tropic_model_port(worker_id),
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
