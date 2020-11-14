#!/usr/bin/env python3
import os
import requests

RELEASES_URL = "https://data.trezor.io/firmware/{}/releases.json"
MODELS = ("1", "T")

FILENAME = os.path.join(os.path.dirname(__file__), "..", "trezorlib", "__init__.py")
START_LINE = "MINIMUM_FIRMWARE_VERSION = {\n"
END_LINE = "}\n"


def version_str(vtuple):
    return ".".join(map(str, vtuple))


def fetch_releases(model):
    version = model
    if model == "T":
        version = "2"

    url = RELEASES_URL.format(version)
    releases = requests.get(url).json()
    releases.sort(key=lambda r: r["version"], reverse=True)
    return releases


def find_latest_required(model):
    releases = fetch_releases(model)
    return next(r for r in releases if r["required"])


with open(FILENAME, "r+") as f:
    output = []
    line = None
    # copy up to & incl START_LINE
    while line != START_LINE:
        line = next(f)
        output.append(line)
    # throw away until END_LINE
    while line != END_LINE:
        line = next(f)
    # append models
    for model in MODELS:
        rel = find_latest_required(model)
        version_tuple = tuple(rel["version"])
        line = f'    "{model}": {version_tuple!r},\n'
        output.append(line)
    output.append(END_LINE)
    # finish reading file
    for line in f:
        output.append(line)

    f.seek(0)
    f.truncate(0)
    for line in output:
        f.write(line)
