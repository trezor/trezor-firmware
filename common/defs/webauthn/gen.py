#!/usr/bin/env python3
import json
import sys
from glob import glob
from hashlib import sha256

try:
    opt = sys.argv[1]
except IndexError:
    print("Usage: gen.py [core|mcu|check])")
    sys.exit(1)


def c_bytes(h):
    return "{ " + ", ".join(["0x%02x" % x for x in h]) + " }"


def gen_core(data):
    print("_knownapps = {")
    print("    # U2F")
    for d in data:
        for url in d.get("u2f", []):
            label = d["label"]
            print('    "%s": {"label": "%s", "use_sign_count": True},' % (url, label))
    print("    # WebAuthn")
    for d in data:
        for origin in d.get("webauthn", []):
            label, use_sign_count = (d["label"], d.get("use_sign_count", None))
            if use_sign_count is None:
                print('    "%s": {"label": "%s"},' % (origin, label))
            else:
                print(
                    '    "%s": {"label": "%s", "use_sign_count": %s},'
                    % (origin, label, use_sign_count)
                )
    print("}")


def gen_mcu(data):
    for d in data:
        for url in d.get("u2f", []):
            label = d["label"]
            h = sha256(url.encode()).digest()
            print(
                '\t{\n\t\t// U2F: %s\n\t\t%s,\n\t\t"%s"\n\t},'
                % (url, c_bytes(h), label)
            )
        for origin in d.get("webauthn", []):
            label = d["label"]
            h = sha256(origin.encode()).digest()
            print(
                '\t{\n\t\t// WebAuthn: %s\n\t\t%s,\n\t\t"%s"\n\t},'
                % (origin, c_bytes(h), label)
            )


data = []
for fn in sorted(glob("apps/*.json")):
    d = json.load(open(fn, "rt"))
    data.append(d)

if opt == "core":
    gen_core(data)
elif opt == "mcu":
    gen_mcu(data)
