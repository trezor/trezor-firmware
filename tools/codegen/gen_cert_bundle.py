#!/usr/bin/python3

from base64 import b64decode
from hashlib import sha256
import requests


REPO = "certifi/python-certifi"


def fetch_certdata():
    r = requests.get("https://api.github.com/repos/%s/git/refs/heads/master" % REPO)
    assert r.status_code == 200
    commithash = r.json()["object"]["sha"]

    r = requests.get(
        "https://raw.githubusercontent.com/%s/%s/certifi/cacert.pem"
        % (REPO, commithash)
    )
    assert r.status_code == 200
    certdata = r.text

    return commithash, certdata


def process_certdata(data):
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


def main():
    commithash, certdata = fetch_certdata()

    print("# fetched from https://github.com/%s" % REPO)
    print("# commit %s" % commithash)

    certs = process_certdata(certdata)

    size = sum([len(x) for x in certs.values()])
    print(
        "# certs: %d | digests size: %d | total size: %d"
        % (len(certs), len(certs) * 32, size)
    )

    print("cert_bundle = [")
    for k, v in certs.items():
        h = sha256(v)
        print("  # %s" % k)
        print("  # %s" % h.hexdigest())
        print("  %s," % h.digest())
    print("]")


if __name__ == "__main__":
    main()
