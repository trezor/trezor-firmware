#!/usr/bin/env python3
"""Attach founder signatures to a PREPARED release (prepare / sign / attach).

Keyless byte patch: signatures land in unauthenticated space (boot header
unauth region, nRF unprotected TLVs), so no digest moves. See
docs/core/build/xtask.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trezor_core_tools import firmware_module, nrf_tree
from trezorlib._internal import firmware_headers

KEY_SET_DEV = {"devel": True, "production": False}


def _attach_model(
    model: str, body: dict, model_dir: Path, sigs: dict, dev_keys: bool
) -> None:
    bl_path = model_dir / body["bootloader"]["file"]
    bl = firmware_headers.BootloaderV2Image.parse(bl_path.read_bytes())

    if bl.signature_present():
        raise SystemExit(f"{bl_path} is already signed -- nothing to attach")

    root = bl.merkle_root()
    if root.hex() != sigs["model_root"]:
        raise SystemExit(
            f"{model}: these signatures are for modelRoot "
            f"{sigs['model_root'][:16]}… but the prepared bootloader folds to "
            f"{root.hex()[:16]}… -- wrong release, or it was re-prepared"
        )
    # The container's sigmask is a record; the header's copy is authenticated.
    recorded = body["bootloader"].get("sigmask")
    if recorded is not None and recorded != bl.header.sigmask:
        raise SystemExit(
            f"{model}: the container records sigmask 0x{recorded:02x} but the "
            f"prepared header committed 0x{bl.header.sigmask:02x} -- the "
            "container does not describe this bootloader"
        )
    if bl.header.sigmask != sigs["sigmask"]:
        raise SystemExit(
            f"{model}: the signature set names sigmask 0x{sigs['sigmask']:02x} "
            f"but the prepared header committed 0x{bl.header.sigmask:02x}; "
            "sigmask is authenticated, so these cannot belong together"
        )

    slh = [bytes.fromhex(h) for h in sigs["slh"]]
    ec = [bytes.fromhex(h) for h in sigs["ec"]]
    for idx, sig in enumerate(slh):
        bl.unauth.slh_signatures[idx] = sig
    for idx, sig in enumerate(ec):
        bl.unauth.ec_signatures[idx] = sig

    # Patching unauth must not move the digest.
    if bl.merkle_root() != root:
        raise SystemExit(
            f"{model}: attaching moved the digest -- a signature was written "
            "into authenticated space, which is a format bug"
        )
    bl.verify(dev_keys=dev_keys)
    bl_path.write_bytes(bl.build())
    print(f"  {model:8} bootloader signed, signature verifies")

    # PQ-native co-processors embed the same signature bytes.
    for entry in body.get("coprocessors", []):
        path = model_dir / entry["file"]
        image = path.read_bytes()
        if not nrf_tree.has_pq_material(image):
            print(f"  {model:8} {entry['kind']}: not PQ-native, nothing to attach")
            continue
        co_path = [bytes.fromhex(n) for n in entry["co_path"]]
        filled = nrf_tree.fill_pq_material(image, slh, ec, co_path)
        # Reserved space: the recorded length and image_hash describe this size.
        if len(filled) != len(image):
            raise SystemExit(
                f"{model}: filling the {entry['kind']} founder records changed "
                f"its length ({len(image)} -> {len(filled)}); the reserved "
                "space did not match"
            )
        path.write_bytes(filled)
        print(f"  {model:8} {entry['kind']}: founder records filled in place")


def attach(bundle_path: Path, tree_dir: Path, sig_path: Path) -> None:
    sig_doc = json.loads(sig_path.read_text())
    expect = f"{firmware_module.CONTAINER_MAGIC}-sig"
    if sig_doc.get("format") != expect:
        raise SystemExit(
            f"{sig_path}: format is {sig_doc.get('format')!r}, expected {expect!r}"
        )
    if sig_doc.get("format_version") != firmware_module.CONTAINER_VERSION:
        raise SystemExit(
            f"{sig_path} is v{sig_doc.get('format_version')}, but this tool "
            f"speaks v{firmware_module.CONTAINER_VERSION}"
        )
    key_set = sig_doc.get("key_set")
    if key_set not in KEY_SET_DEV:
        raise SystemExit(f"{sig_path}: unknown key_set {key_set!r}")

    doc = json.loads(bundle_path.read_text())
    models = firmware_module.container_models(doc, bundle_path)

    missing = sorted(set(models) - set(sig_doc.get("models", {})))
    if missing:
        raise SystemExit(
            f"{sig_path} has no signatures for {', '.join(missing)} -- a "
            "partly signed release is not a release"
        )
    extra = sorted(set(sig_doc["models"]) - set(models))
    if extra:
        raise SystemExit(
            f"{sig_path} carries signatures for {', '.join(extra)}, which this "
            "release does not contain"
        )

    print(f"attaching {key_set} signatures to {tree_dir}")
    for model, body in sorted(models.items()):
        model_dir = tree_dir if "models" not in doc else tree_dir / model
        _attach_model(
            model, body, model_dir, sig_doc["models"][model], KEY_SET_DEV[key_set]
        )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="the prepared release's manifest: a cross-model set "
        "(bundle[_devel].json) or one model's bundle.json",
    )
    ap.add_argument(
        "--tree",
        type=Path,
        required=True,
        help="the directory the manifest describes",
    )
    ap.add_argument(
        "--signatures", type=Path, required=True, help="the signature set to attach"
    )
    args = ap.parse_args()
    attach(args.bundle, args.tree, args.signatures)


if __name__ == "__main__":
    main()
