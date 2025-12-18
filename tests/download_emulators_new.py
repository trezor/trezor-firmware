#!/usr/bin/env python3
import subprocess
import sys
from http import HTTPStatus
from pathlib import Path
from typing import TypeAlias

import requests

EmulatorDict: TypeAlias = dict[str, list[str]]


T1B1 = "T1B1"
LEGACY = [T1B1]

T2T1 = "T2T1"
T2B1 = "T2B1"
T3B1 = "T3B1"
T3T1 = "T3T1"
T3W1 = "T3W1"
CORE = [T2T1, T2B1, T3B1, T3T1, T3W1]

ALL_MODELS = [*LEGACY, *CORE]

OLDEST_AVAILABLE_LEGACY = (1, 6, 2)
OLDEST_AVAILABLE_CORE = (2, 0, 8)

RELEASES = "https://raw.githubusercontent.com/trezor/trezor-firmware/refs/heads/main/common/releases.json"

PATH_PREFIX_NEW = "https://data.trezor.io/dev/firmware/releases/emulators-new"
PATH_PREFIX_OLD = "https://data.trezor.io/dev/firmware/releases/emulators"

BASE_DIR = "./emulators"


class MissingArtifactError(Exception):
    model: str
    version: str

    def __init__(self, model: str, version: str, *args) -> None:
        self.model = model
        self.version = version
        super().__init__(*args)


class KnownMissingArtifactError(MissingArtifactError):
    pass


class UnknownModelError(RuntimeError):
    model: str

    def __init__(self, model: str, *args):
        self.model = model
        super().__init__(*args)

    def __str__(self):
        return f"UnknownModelError(model={self.model})"


class Emulator:
    version: str
    model: str
    url: str
    save_path: Path | None = None

    def __init__(self, version: str, model: str, url: str) -> None:
        self.version = version
        self.model = model
        self.url = url

    def download(
        self, save_path: Path | None = None, skip_if_exists: bool = True
    ) -> None:
        if save_path is None:
            save_path = self._get_default_save_path()

        self.save_path = save_path

        if save_path.exists() and skip_if_exists:
            # Skipping
            return

        # Make sure that all parent directories exist.
        # If not, create them.
        save_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Downloading from {self.url} to {save_path}")
        with requests.get(self.url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def set_as_executable(self) -> None:
        if self.save_path is None:
            # Run `download` first
            raise RuntimeError
        subprocess.run(["chmod", "u+x", self.save_path], check=True)

    def get_dir(self) -> Path:
        if self.save_path is None:
            # Run `download` first
            raise RuntimeError
        return self.save_path.parent

    def _get_filename(self):
        return (
            f"trezor-emu-{get_legacy_or_core(self.model)}-{self.model}-v{self.version}"
        )

    def _get_default_save_path(self) -> Path:
        return Path(BASE_DIR) / self.model / self._get_filename()


def get_legacy_or_core(model: str) -> str:
    if model in LEGACY:
        return "legacy"
    if model in CORE:
        return "core"
    raise UnknownModelError(model)


def _get_path_new(model: str, version: str) -> str:
    return f"{PATH_PREFIX_NEW}/{model}/trezor-emu-{get_legacy_or_core(model)}-{model}-v{version}"


def _get_path_old(model: str, version: str) -> str:
    return f"{PATH_PREFIX_OLD}/trezor-emu-{get_legacy_or_core(model)}-v{version}"


def skip_old_unavailable_versions(version: str, model: str) -> None:
    version_tuple = tuple(int(part) for part in version.split("."))
    if model in LEGACY:
        if version_tuple < OLDEST_AVAILABLE_LEGACY:
            raise KnownMissingArtifactError(model, version)
    if model in CORE:
        if version_tuple < OLDEST_AVAILABLE_CORE:
            raise KnownMissingArtifactError(model, version)


def get_availability_status(url: str) -> int:
    status_code = requests.head(url, timeout=10).status_code
    return status_code


def get_path(version: str, model: str) -> str:

    # The oldest emulators are not available
    skip_old_unavailable_versions(version, model)

    path = _get_path_new(model, version)
    status = get_availability_status(path)
    if status == HTTPStatus.OK:
        return path

    # Some of the older T1B1 and T2T1 emulators are stored elsewhere
    if not status == HTTPStatus.NOT_FOUND or model not in (T1B1, T2T1):
        raise MissingArtifactError(model, version)

    path = _get_path_old(model, version)
    if get_availability_status(path) == HTTPStatus.OK:
        return path
    raise MissingArtifactError(model, version)


def get_all_releases() -> EmulatorDict:
    releases: dict[str, EmulatorDict] = requests.get(RELEASES).json()
    return releases["firmware"]


def get_emulators_for_model(model: str, firmwares: EmulatorDict) -> list[Emulator]:
    emulators: list[Emulator] = []
    for version, models in firmwares.items():
        if model in models:
            try:
                path = get_path(version, model)
                emulators.append(Emulator(version, model, path))
            except KnownMissingArtifactError:
                # Old artifacts that are known to be unavailable
                pass
            except MissingArtifactError as e:
                print(
                    f"Artifact for model {e.model}, version: {e.version} is unavailable!"
                )
    return emulators


def download_emulators_for_model(model: str) -> None:
    if model not in ALL_MODELS:
        raise UnknownModelError(model)

    all_releases = get_all_releases()
    emus = get_emulators_for_model(model, all_releases)

    for emu in emus:
        emu.download()
        emu.set_as_executable()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_emulators_new.py <model>")
        sys.exit(1)
    model = sys.argv[1]
    download_emulators_for_model(model)
