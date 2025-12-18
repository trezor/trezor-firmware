#!/usr/bin/env python3
import json
import stat
from http import HTTPStatus
from pathlib import Path
from typing import TypeAlias

import click
import requests
from emulators import gen_from_model

from trezorlib.models import ALL_MODELS

EmulatorDict: TypeAlias = dict[str, list[str]]

ALL_MODEL_NAMES = sorted(m.internal_name for m in ALL_MODELS)

OLDEST_AVAILABLE = {
    "legacy": (1, 6, 2),
    "core": (2, 0, 8),
}

EMULATORS_URL_PREFIX = "https://data.trezor.io/dev/firmware/releases/emulators-new"

TESTS_DIR = Path(__file__).resolve().parent
SAVE_DIR = TESTS_DIR / "emulators"
RELEASES_JSON = TESTS_DIR.parent / "common" / "releases.json"


class MissingArtifactError(Exception):
    model: str
    version: str

    def __init__(self, model: str, version: str) -> None:
        self.model = model
        self.version = version
        super().__init__()


class KnownMissingArtifactError(MissingArtifactError):
    pass


class Emulator:
    version: str
    model: str
    url: str
    save_path: Path | None = None

    def __init__(self, version: str, model: str) -> None:
        self.version = version
        self.model = model
        self.url = self._get_download_url()

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

        click.echo(f"Downloading from {self.url} to {save_path}")
        with requests.get(self.url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def set_as_executable(self) -> None:
        if self.save_path is None:
            raise click.ClickException("Run `download` first")

        path = Path(self.save_path)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def check_download_availability(self) -> None:

        version_tuple = tuple(int(part) for part in self.version.split("."))
        if version_tuple < OLDEST_AVAILABLE[gen_from_model(self.model)]:
            # Is old known-to-be-unavailable version
            raise KnownMissingArtifactError(self.model, self.version)

        status_code = requests.head(self.url, timeout=10).status_code
        if status_code != HTTPStatus.OK:
            # Not available for download
            raise MissingArtifactError(self.model, self.version)

    def _get_filename(self) -> str:
        return f"trezor-emu-{gen_from_model(self.model)}-{self.model}-v{self.version}"

    def _get_default_save_path(self) -> Path:
        return SAVE_DIR / self.model / self._get_filename()

    def _get_download_url(self) -> str:
        return f"{EMULATORS_URL_PREFIX}/{self.model}/{self._get_filename()}"


def get_all_releases() -> EmulatorDict:
    with RELEASES_JSON.open(encoding="utf-8") as f:
        releases: dict[str, EmulatorDict] = json.load(f)
    return releases["firmware"]


def get_emulators_for_model(model: str, firmwares: EmulatorDict) -> list[Emulator]:
    emulators: list[Emulator] = []
    for version, models in firmwares.items():
        if model in models:
            try:
                emu = Emulator(version, model)
                emu.check_download_availability()
                emulators.append(emu)
            except KnownMissingArtifactError:
                # Old artifacts that are known to be unavailable
                pass
            except MissingArtifactError as e:
                click.echo(
                    f"Artifact for model {e.model}, version: {e.version} is unavailable!"
                )
    return emulators


def download_emulators_for_model(model: str) -> None:
    if model not in ALL_MODEL_NAMES:
        raise ValueError(f"Unknown model: {model}")

    all_releases = get_all_releases()
    emus = get_emulators_for_model(model, all_releases)

    for emu in emus:
        emu.download()
        emu.set_as_executable()


@click.command()
@click.argument("model", type=click.Choice(ALL_MODEL_NAMES, case_sensitive=True))
def main(model: str) -> None:
    """
    Download all available emulators for a given Trezor model.
    """
    download_emulators_for_model(model)


if __name__ == "__main__":
    main()
