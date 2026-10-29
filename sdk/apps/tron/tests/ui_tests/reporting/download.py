from __future__ import annotations

import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import requests

RECORDS_WEBSITE = "https://data.trezor.io/dev/firmware/ui_tests/"
MASTER_WEBSITE = "https://raw.githubusercontent.com/trezor/trezor-firmware/master/"
FIXTURES_CURRENT = Path(__file__).resolve().parent.parent / "fixtures.json"


def fetch_recorded(hash: str, path: Path) -> None:
    zip_src = RECORDS_WEBSITE + hash + ".zip"

    try:
        dest, _ = urllib.request.urlretrieve(zip_src)
    except urllib.error.HTTPError:
        raise RuntimeError(f"No such recorded collection was found on '{zip_src}'.")

    with zipfile.ZipFile(dest, "r") as z:
        z.extractall(path)

    Path(dest).unlink()


class MasterFixturesMissing(Exception):
    """Master has no fixtures for this app yet."""


def fixtures_master_url() -> str:
    """URL of this app's fixtures.json on master."""
    for root in FIXTURES_CURRENT.parents:
        if (root / ".git").exists():
            return MASTER_WEBSITE + FIXTURES_CURRENT.relative_to(root).as_posix()
    raise RuntimeError(f"{FIXTURES_CURRENT} is not in a git checkout")


def fetch_fixtures_master() -> dict[str, Any]:
    url = fixtures_master_url()
    r = requests.get(url)
    if r.status_code == 404:
        raise MasterFixturesMissing(url)
    r.raise_for_status()
    return r.json()
