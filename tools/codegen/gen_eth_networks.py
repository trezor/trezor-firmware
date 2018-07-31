#!/usr/bin/env python3
import json

j = json.load(open("../../vendor/trezor-common/defs/ethereum/networks.json", "r"))

print("NETWORKS = [")

for n in j:
    print("    NetworkInfo(")
    for f in ["chain_id", "slip44", "shortcut", "name", "rskip60"]:
        print("        %s=%s," % (f, repr(n[f])))
    print("    ),")

print("]")
