#!/usr/bin/env python3
"""Fold a custom firmware into an ALREADY-signed firmware_root. No keys.

`firmware_pq_sign.py` cuts a new tree: it computes every variant's leaf, builds
firmware_root over them, and re-signs the bootloader header. A custom
(unofficial) build cannot do that -- it has no founder key -- and does not need
to, because the CUSTOM variant's leaf is code-independent: the authenticity fold
zeroes the firmware version and the app entry's `size` + `code_hash`, so any
creator's app reaches the one founder-signed custom slot.

So this tool does the keyless half of signing:

  1. fill the manifest's code_hashes over the placed code (the build emits a
     template with them zeroed),
  2. recompute this image's custom leaf and CHECK it against the leaf the
     committed bundle records -- the whole point, since a leaf that does not
     match will not fold, and without this check that only surfaces as a
     rejected install,
  3. bake the committed co-path into the manifest region, so the image is
     self-contained exactly as a signed one is.

The bootloader is never touched: it already carries the signed firmware_root.

What must match for step 2 to hold is everything the fold does NOT zero -- the
module count, each entry's type / flags / addr / chunk_size, and the WHOLE
secmon entry. The secmon is founder-bound even for custom, which is why a custom
build has to embed the committed secmon rather than a freshly built one. When
the leaf does not match, the diff is reported field by field instead of as a
bare hash mismatch.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zipfile
from pathlib import Path

from trezor_core_tools import firmware_module

# Manifest layout, mirroring trezorlib.firmware.pq_secure: a fixed header then
# one entry per module. Used only to name the field that differs when a leaf
# fails to match, so a creator is told WHICH input is wrong.
_HEADER = struct.Struct("<4sIIII")  # magic, variant, version, translations, count
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
    models = raw["models"] if "models" in raw else None
    name: str
    if models is None:
        body = raw
        name = model or raw.get("nrf", {}).get("model_id") or "?"
    else:
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
            if v.get("firmware_type") == firmware_module.FW_VARIANT_CUSTOM
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
    ap.add_argument(
        "--zip-out",
        type=Path,
        help="also write the portable release zip that `trezorctl firmware update -f` "
        "consumes -- without it an earlier release's zip stays behind and installs "
        "a stale image",
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
    if variant != firmware_module.FW_VARIANT_CUSTOM:
        raise SystemExit(
            f"{args.firmware} is variant {variant}, not CUSTOM "
            f"({firmware_module.FW_VARIANT_CUSTOM}) -- only the custom slot is "
            "presigned; an official variant's leaf moves with its code and needs "
            "a fresh release"
        )

    # 2. the check that makes this worth doing as a build step.
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

    if args.zip_out is not None:
        # The same flat archive `firmware_pq_sign.py --zip-out` writes, holding
        # only what a presigned custom release consists of: the committed
        # bootloader, this one image, the bundle, and the nRF image. Written here
        # because the image is only self-contained once the proof is baked in.
        release = args.firmware.parent
        members = [release / "bootloader.bin", args.firmware, release / "bundle.json"]
        members += sorted(release.glob("trezor-ble*.bin"))
        args.zip_out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
            for member in members:
                if not member.is_file():
                    raise SystemExit(f"{member} is missing from the release")
                zf.write(member, member.name)
        print(f"  zip {args.zip_out} ({', '.join(m.name for m in members)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
