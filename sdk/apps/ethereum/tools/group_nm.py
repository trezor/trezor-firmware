#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict

line_re = re.compile(r"^\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(.+)$")
hash_re = re.compile(r"::h[0-9a-f]{16}$")
MIN_PRINT_SIZE = int(os.getenv("NM_MIN_SIZE", "50"))


def split_module(sym: str) -> str:
    m = re.match(r"^([A-Za-z_]\w*)::([A-Za-z_]\w*)::", sym)
    if m:
        return f"{m.group(1)}::{m.group(2)}"

    toks = re.findall(r"([A-Za-z_]\w*)::", sym)
    if len(toks) >= 2:
        return f"{toks[0]}::{toks[1]}"
    if len(toks) == 1:
        return f"{toks[0]}::(root)"
    return "(other)::(other)"


mods = defaultdict(lambda: {"bytes": 0, "funcs": []})

for line in sys.stdin:
    m = line_re.match(line)
    if not m:
        continue

    addr_hex, size_hex, typ, sym = m.groups()
    if typ not in "bdrD":
        continue
    if sym.startswith(".L"):
        continue

    size = int(size_hex, 16)
    sym = hash_re.sub("", sym.strip())
    mod = split_module(sym)

    mods[mod]["bytes"] += size
    mods[mod]["funcs"].append((size, addr_hex, typ, sym))

total_bytes = sum(data["bytes"] for data in mods.values()) or 1

print(f"=== Module summary (all funcs, print cutoff={MIN_PRINT_SIZE}) ===")
for mod, data in sorted(mods.items(), key=lambda kv: kv[1]["bytes"], reverse=True):
    shown = sum(1 for f in data["funcs"] if f[0] >= MIN_PRINT_SIZE)
    pct_total = (data["bytes"] * 100.0) / total_bytes
    print(
        f"{mod}: bytes={data['bytes']} ({pct_total:.2f}%) "
        f"funcs={len(data['funcs'])} shown={shown}"
    )

print(f"\n=== Functions by module (size >= {MIN_PRINT_SIZE}) ===")
for mod, data in sorted(mods.items(), key=lambda kv: kv[1]["bytes"], reverse=True):
    funcs = [f for f in data["funcs"] if f[0] >= MIN_PRINT_SIZE]
    if not funcs:
        continue

    pct_total = (data["bytes"] * 100.0) / total_bytes
    print(
        f"\n[{mod}] total_bytes={data['bytes']} ({pct_total:.2f}%) "
        f"total_funcs={len(data['funcs'])} funcs above {MIN_PRINT_SIZE} bytes:"
    )
    for size, addr_hex, typ, sym in sorted(funcs, key=lambda x: x[0], reverse=True):
        print(f"  {size:6d} 0x{addr_hex} {typ} {sym}")
