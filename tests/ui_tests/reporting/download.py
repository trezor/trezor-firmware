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

_dns_failed = False


def fetch_recorded(hash, path):
    global _dns_failed

    if _dns_failed:
        raise RuntimeError("Not trying firmware.corp.sldev.cz again after DNS failure.")

    zip_src = RECORDS_WEBSITE + hash + ".zip"
    zip_dest = path / "recorded.zip"

    try:
        urllib.request.urlretrieve(zip_src, zip_dest)
    except urllib.error.HTTPError:
        raise RuntimeError(f"No such recorded collection was found on '{zip_src}'.")
    except urllib.error.URLError:
        _dns_failed = True
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
