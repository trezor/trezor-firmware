# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import requests

RECORDS_WEBSITE = "https://data.trezor.io/dev/firmware/ui_tests/"
FIXTURES_MASTER = "https://raw.githubusercontent.com/trezor/trezor-firmware/master/tests/ui_tests/fixtures.json"
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


def fetch_fixtures_master() -> dict[str, Any]:
    r = requests.get(FIXTURES_MASTER)
    r.raise_for_status()
    return r.json()
