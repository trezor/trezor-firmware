import json
import pathlib
import urllib.error
import urllib.request
import zipfile
from typing import Dict

import requests

RECORDS_WEBSITE = "https://firmware.corp.sldev.cz/ui_tests/"
FIXTURES_MASTER = "https://raw.githubusercontent.com/trezor/trezor-firmware/master/tests/ui_tests/fixtures.json"
FIXTURES_CURRENT = pathlib.Path(__file__).parent / "../fixtures.json"


def fetch_recorded(hash, path):
    zip_src = RECORDS_WEBSITE + hash + ".zip"
    zip_dest = path / "recorded.zip"

    try:
        urllib.request.urlretrieve(zip_src, zip_dest)
    except urllib.error.HTTPError:
        raise RuntimeError("No such recorded collection was found on '%s'." % zip_src)
    except urllib.error.URLError:
        raise RuntimeError(
            "Server firmware.corp.sldev.cz could not be found. Are you on VPN?"
        )

    with zipfile.ZipFile(zip_dest, "r") as z:
        z.extractall(path)

    zip_dest.unlink()


def fetch_fixtures_master() -> Dict[str, str]:
    r = requests.get(FIXTURES_MASTER)
    r.raise_for_status()
    return r.json()


def fetch_fixtures_current() -> Dict[str, str]:
    with open(FIXTURES_CURRENT) as f:
        return json.loads(f.read())
