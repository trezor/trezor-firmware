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
    print("# contents generated via script in")
    print("# trezor-common/defs/webauthn/gen.py")
    print("# do not edit manually")
    print()
    print("knownapps = {")
    print("    # U2F")
    for d in data:
        for appid in d.get("u2f", []):
            label = d["label"]
            h = bytes.fromhex(appid)
            print("    %s: {" % h)
            print('        "label": "%s",' % label)
            print('        "use_sign_count": True,')
            print("    },")
    print("    # WebAuthn")
    for d in data:
        for origin in d.get("webauthn", []):
            h = sha256(origin.encode()).digest()
            label, use_sign_count = (d["label"], d.get("use_sign_count", None))
            print("    %s: {" % h)
            print('        "label": "%s",' % label)
            if use_sign_count is not None:
                print('        "use_sign_count": %s,' % use_sign_count)
            print("    },")
    print("}")


def gen_mcu(data):
    for d in data:
        for appid in d.get("u2f", []):
            label = d["label"]
            h = bytes.fromhex(appid)
            print('\t{\n\t\t// U2F\n\t\t%s,\n\t\t"%s"\n\t},' % (c_bytes(h), label))
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
