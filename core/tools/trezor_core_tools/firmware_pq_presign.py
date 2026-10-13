#!/usr/bin/env python3
"""Fold a custom firmware into an ALREADY-signed firmware_root. No keys.

The CUSTOM leaf is code-independent (the fold zeroes firmware version and the
app entry's size + code_hash), so: fill code_hashes, check the leaf against the
committed bundle, bake in the committed co-path. Bootloader untouched.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

from trezor_core_tools import firmware_module

# Manifest layout (mirrors trezorlib.firmware.pq_secure), used only to name the
# differing field. translations_root is a 32-byte hash, not a word.
_HEADER = struct.Struct("<4sII32sI")
_ENTRY = struct.Struct("<IIIII32s")  # type, flags, addr, chunk_size, size, code_hash
_MODULE_NAMES = {1: "secmon", 2: "app"}


def _describe_difference(mine: bytes, theirs: bytes) -> list[str]:
    """Name the manifest fields that differ, most useful first."""
    out: list[str] = []
    if len(mine) != len(theirs):
        return [f"manifest length {len(mine)} vs {len(theirs)} -- module count differs"]

    m_hdr = _HEADER.unpack_from(mine, 0)
    t_hdr = _HEADER.unpack_from(theirs, 0)
    for name, a, b in zip(
        (
            "magic",
            "firmware_variant",
            "firmware_version",
            "translations_root",
            "module_count",
        ),
        m_hdr,
        t_hdr,
    ):
        if a != b:
            out.append(f"{name}: {a!r} vs {b!r}")

    count = min(m_hdr[4], t_hdr[4])
    for i in range(count):
        off = _HEADER.size + i * _ENTRY.size
        m_ent = _ENTRY.unpack_from(mine, off)
        t_ent = _ENTRY.unpack_from(theirs, off)
        label = _MODULE_NAMES.get(m_ent[0], f"module type {m_ent[0]}")
        for field, a, b in zip(
            ("module_type", "flags", "addr", "chunk_size", "size", "code_hash"),
            m_ent,
            t_ent,
        ):
            if a != b:
                shown = (
                    (a.hex()[:16] + "…", b.hex()[:16] + "…")
                    if isinstance(a, bytes)
                    else (a, b)
                )
                out.append(f"{label}.{field}: {shown[0]} vs {shown[1]}")
    return out or ["no field differs, yet the leaves do not match"]


def _custom_entry(bundle_path: Path, model: str | None) -> tuple[dict, str]:
    """The bundle's CUSTOM variant entry, from either bundle shape."""
    raw = json.loads(bundle_path.read_text())
    models = firmware_module.container_models(raw, bundle_path)
    if model is None:
        if len(models) != 1:
            raise SystemExit(
                f"{bundle_path} covers {', '.join(sorted(models))} -- "
                "pass --model to say which one this firmware is for"
            )
        name = next(iter(models))
    else:
        name = model
    if name not in models:
        raise SystemExit(f"{bundle_path} has no entry for {name}")
    body = models[name]

    entry = next(
        (
            v
            for v in body["variants"]
            if v.get("firmware_type") == firmware_module.FW_VARIANT_SEC_CUSTOM
        ),
        None,
    )
    if entry is None:
        raise SystemExit(
            f"{bundle_path} records no CUSTOM variant for {name}, so there is no "
            "presigned slot to fold into"
        )
    return entry, name


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument(
        "--firmware",
        type=Path,
        required=True,
        help="custom firmware.bin, patched in place",
    )
    ap.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="the committed bundle whose signed firmware_root this image folds into",
    )
    ap.add_argument(
        "--model", help="which model's entry to use (default: the only one)"
    )
    args = ap.parse_args()

    entry, model = _custom_entry(args.bundle, args.model)
    expected_leaf = bytes.fromhex(entry["leaf"])
    proof = [bytes.fromhex(n) for n in entry["proof"]]

    fw = bytearray(args.firmware.read_bytes())
    if not firmware_module.manifest_entries(fw):
        raise SystemExit(f"{args.firmware}: no manifest modules found")

    # 1. real code hashes over the placed code, at each entry's chunk_size.
    firmware_module.fill_manifest(fw)
    manifest = firmware_module.read_manifest(fw)

    variant = firmware_module.manifest_variant(manifest)
    if variant != firmware_module.FW_VARIANT_SEC_CUSTOM:
        raise SystemExit(
            f"{args.firmware} is variant {variant}, not CUSTOM "
            f"({firmware_module.FW_VARIANT_SEC_CUSTOM}) -- only the custom slot is "
            "presigned; an official variant's leaf moves with its code and needs "
            "a fresh release"
        )

    # 2. the leaf must match the committed one, or it will not fold.
    leaf = firmware_module.variant_leaf(manifest)
    if leaf != expected_leaf:
        mine = firmware_module.authenticity_manifest(manifest)
        stored = entry.get("authenticity_manifest")
        print(
            f"this image's custom leaf is {leaf.hex()[:16]}…, but {model}'s signed "
            f"slot is {expected_leaf.hex()[:16]}… -- it would not fold",
            file=sys.stderr,
        )
        if stored:
            for line in _describe_difference(mine, bytes.fromhex(stored)):
                print(f"  {line}", file=sys.stderr)
            print(
                "  (the app's size and code_hash are zeroed by the fold, so a "
                "difference there is not the cause)",
                file=sys.stderr,
            )
        else:
            print(
                "  the bundle carries no authenticity_manifest, so the differing "
                "field cannot be named -- re-cut the release to record it",
                file=sys.stderr,
            )
        return 1

    # 3. bake the committed co-path in, and read it back.
    firmware_module.install_manifest_proof(fw, proof)
    args.firmware.write_bytes(fw)
    assert firmware_module.read_manifest_proof(bytes(fw)) == proof

    root = firmware_module._fold_proof(leaf, proof)
    print(f"{args.firmware.name}: custom leaf {leaf.hex()[:16]}… ({model})")
    print(f"  folds through {len(proof)} node(s) to firmware_root {root.hex()[:16]}…")
    print("  proof baked into the manifest region -- no key used, bootloader untouched")

    return 0


if __name__ == "__main__":
    sys.exit(main())
