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
        if "u2f" in d:
            url, label = d["u2f"], d["label"]
            print('    "%s": "%s",' % (url, label))
    print("    # WebAuthn")
    for d in data:
        if "webauthn" in d:
            origin, label = d["webauthn"], d["label"]
            print('    "%s": "%s",' % (origin, label))
    print("}")


def gen_mcu(data):
    for d in data:
        if "u2f" in d:
            url, label = d["u2f"], d["label"]
            h = sha256(url.encode()).digest()
            print(
                '\t{\n\t\t// U2F: %s\n\t\t%s,\n\t\t"%s"\n\t},'
                % (url, c_bytes(h), label)
            )
        if "webauthn" in d:
            origin, label = d["webauthn"], d["label"]
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
