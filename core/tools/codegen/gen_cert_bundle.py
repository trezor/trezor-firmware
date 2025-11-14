#!/usr/bin/env python3
from __future__ import annotations

from base64 import b64decode
from hashlib import sha256

import requests

REPO = "certifi/python-certifi"


def fetch_certdata() -> tuple[str, str]:
    r = requests.get(f"https://api.github.com/repos/{REPO}/git/refs/heads/master")
    assert r.status_code == 200
    commithash = r.json()["object"]["sha"]

    r = requests.get(
        f"https://raw.githubusercontent.com/{REPO}/{commithash}/certifi/cacert.pem"
    )
    assert r.status_code == 200
    certdata = r.text

    return commithash, certdata


def process_certdata(data: str) -> dict[str, bytes]:
    certs = {}
    lines = [x.strip() for x in data.split("\n")]
    label = None
    value = None
    for line in lines:
        if line.startswith("# Label: "):
            assert label is None
            assert value is None
            label = line.split('"')[1]
        elif line == "-----BEGIN CERTIFICATE-----":
            assert label is not None
            assert value is None
            value = ""
        elif line == "-----END CERTIFICATE-----":
            assert label is not None
            assert value is not None
            certs[label] = b64decode(value)
            label, value = None, None
        else:
            if value is not None:
                value += line

    return certs


def main() -> None:
    commithash, certdata = fetch_certdata()

    print(f"# fetched from https://github.com/{REPO}")
    print(f"# commit {commithash}")

    certs = process_certdata(certdata)

    size = sum([len(x) for x in certs.values()])
    print(
        f"# certs: {len(certs)} | digests size: {len(certs) * 32} | total size: {size}"
    )

    print("cert_bundle = [")
    for k, v in certs.items():
        h = sha256(v)
        print(f"  # {k}")
        print(f"  # {h.hexdigest()}" % h.hexdigest())
        print(f"  {h.digest()},")
    print("]")


if __name__ == "__main__":
    main()
