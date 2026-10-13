#!/usr/bin/env python3
"""Prove every copy of the root public keys still agrees.

Copies: trezorlib firmware/models.py (signer), sec/image/inc/sec/root_keys.h
(STM), mcuboot image_validate.c (nRF, standalone repo). Order matters: the
sigmask names keys by index. The nRF copy is skipped when not checked out.
"""

from __future__ import annotations

import re
import sys

from trezorlib.firmware.models import (
    ROOT_ED25519_KEYS,
    ROOT_ED25519_KEYS_DEV,
    ROOT_SLH_DSA_KEYS,
    ROOT_SLH_DSA_KEYS_DEV_PUBLIC,
)

from .common import MODELS_DIR

REPO = MODELS_DIR.parents[2]  # core/embed/models -> repo root
STM_HEADER = REPO / "core/embed/sec/image/inc/sec/root_keys.h"
NRF_SOURCE = REPO / "nordic/bootloader/mcuboot/boot/bootutil/src/image_validate.c"

# Models whose nRF uses the classic scheme; the STM mirrors that per-model pool
# to predict the nRF's verdict before pushing (nrf_image_legacy_accept_ok).
LEGACY_MODELS = {"T3W1"}


def c_string_keys(block: str) -> list[str]:
    """Every 32-byte "\\xNN..." literal in a block of C, in order."""
    out = []
    for lit in re.findall(r'"((?:\\x[0-9a-fA-F]{2})+)"', block):
        raw = bytes(int(h, 16) for h in re.findall(r"\\x([0-9a-fA-F]{2})", lit))
        if len(raw) == 32:
            out.append(raw.hex())
    return out


def between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i : text.index(end, i + len(start))]


def stm_pools(text: str) -> dict[str, list[str]]:
    """The four FOUNDER_*_KEYS_* macro bodies, keyed by pool name."""
    names = [
        "ROOT_SLH_DSA_KEYS_DEV",
        "ROOT_ED25519_KEYS_DEV",
        "ROOT_SLH_DSA_KEYS",
        "ROOT_ED25519_KEYS",
    ]
    out = {}
    for n in names:
        # Whole-identifier match: ROOT_SLH_DSA_KEYS is a prefix of ..._KEYS_DEV.
        m = re.search(rf"#define {re.escape(n)}\b", text)
        if m is None:
            out[n] = []
            continue
        i = m.start()
        # body runs to the next #define, else to the end of the macro block
        ends = [
            e
            for e in (
                text.find("#define ", i + len(n) + 8),
                text.find("// clang-format on", i),
                len(text),
            )
            if e != -1
        ]
        out[n] = c_string_keys(text[i : min(ends)])
    return out


def nrf_pools(text: str) -> dict[str, list[str]]:
    """The nRF's pools: #ifndef MCUBOOT_PRODUCTION_KEY is dev, #else production."""
    block = between(text, "#ifndef MCUBOOT_PRODUCTION_KEY", "#define PQ_KEY_N")
    dev, prod = block.split("#else", 1)
    return {
        "ROOT_SLH_DSA_KEYS_DEV": c_string_keys(between(dev, "PQ_SLH_KEYS[]", "};")),
        "ROOT_ED25519_KEYS_DEV": c_string_keys(between(dev, "PQ_EC_KEYS[]", "};")),
        "ROOT_SLH_DSA_KEYS": c_string_keys(between(prod, "PQ_SLH_KEYS[]", "};")),
        "ROOT_ED25519_KEYS": c_string_keys(between(prod, "PQ_EC_KEYS[]", "};")),
    }


def legacy_stm_pools(text: str) -> dict[str, list[str]]:
    """The MODEL_NRF_LEGACY_KEYS_* macro bodies from a model header."""
    out = {}
    for name in ("MODEL_NRF_LEGACY_KEYS_DEVEL", "MODEL_NRF_LEGACY_KEYS_PRODUCTION"):
        m = re.search(rf"#define {re.escape(name)}\b", text)
        if m is None:
            out[name] = []
            continue
        i = m.start()
        ends = [
            e for e in (text.find("#define ", i + len(name) + 8), len(text)) if e != -1
        ]
        out[name] = c_string_keys(text[i : min(ends)])
    return out


def legacy_nrf_pools(text: str) -> dict[str, list[str]]:
    """MCUboot's classic BOOTLOADER_KEYS (under #ifndef CONFIG_BOOT_PQ_SECURE_BOOT),
    dev in the #ifndef MCUBOOT_PRODUCTION_KEY arm, production in the #else."""
    i = text.index("#ifndef CONFIG_BOOT_PQ_SECURE_BOOT")
    block = text[i : text.index("#endif /* !CONFIG_BOOT_PQ_SECURE_BOOT */", i)]
    dev, prod = block.split("#else", 1)
    return {
        "MODEL_NRF_LEGACY_KEYS_DEVEL": c_string_keys(dev),
        "MODEL_NRF_LEGACY_KEYS_PRODUCTION": c_string_keys(prod),
    }


def check_legacy() -> bool:
    """Compare each legacy model's mirrored pool against MCUboot's. True on failure."""
    if not NRF_SOURCE.is_file():
        print(f"SKIP legacy: {NRF_SOURCE} not present")
        return False
    want = legacy_nrf_pools(NRF_SOURCE.read_text())
    failed = False
    for model in sorted(LEGACY_MODELS):
        header = MODELS_DIR / model / f"model_{model}.h"
        if not header.is_file():
            print(f"FAIL legacy {model}: {header} missing")
            failed = True
            continue
        got = legacy_stm_pools(header.read_text())
        for pool, expected in want.items():
            if got.get(pool) == expected:
                print(f"OK   {model} model_{model}.h: {pool} ({len(expected)} keys)")
                continue
            failed = True
            print(f"FAIL {model} model_{model}.h: {pool}")
            print(f"       mcuboot: {expected}")
            print(f"       found:   {got.get(pool)}")
            if sorted(got.get(pool) or []) == sorted(expected):
                print("       -> same keys, DIFFERENT ORDER. The sigmask selects by")
                print("          index, so this makes the STM predict the wrong keys.")
    return failed


def main() -> int:
    expected = {
        "ROOT_SLH_DSA_KEYS_DEV": [k.hex() for k in ROOT_SLH_DSA_KEYS_DEV_PUBLIC],
        "ROOT_ED25519_KEYS_DEV": [k.hex() for k in ROOT_ED25519_KEYS_DEV],
        "ROOT_SLH_DSA_KEYS": [k.hex() for k in ROOT_SLH_DSA_KEYS],
        "ROOT_ED25519_KEYS": [k.hex() for k in ROOT_ED25519_KEYS],
    }

    sources = [("STM  root_keys.h", stm_pools(STM_HEADER.read_text()))]
    if NRF_SOURCE.is_file():
        sources.append(("nRF  image_validate.c", nrf_pools(NRF_SOURCE.read_text())))
    else:
        print(f"SKIP nRF: {NRF_SOURCE} not present (west workspace not checked out)")

    failed = False
    for label, pools in sources:
        for pool, want in expected.items():
            got = pools.get(pool, [])
            if got == want:
                print(f"OK   {label}: {pool} ({len(got)} keys)")
                continue
            failed = True
            print(f"FAIL {label}: {pool}")
            print(f"       trezorlib: {want}")
            print(f"       found:     {got}")
            if sorted(got) == sorted(want):
                print("       -> same keys, DIFFERENT ORDER. The sigmask indexes by")
                print("          position, so this invalidates existing signatures.")

    if check_legacy():
        failed = True

    if failed:
        print("\nkey copies DIVERGED -- fix before building or signing")
        return 1
    print("\nall key copies agree (root + co-processor legacy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
