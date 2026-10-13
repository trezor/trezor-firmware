#!/usr/bin/env python3
"""Sign a PREPARED release with development keys (the ceremony's stand-in).

Reads each model's modelRoot from the prepared bootloader (cross-checked against
its manifest) and writes a signature set for firmware_pq_attach.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trezor_core_tools import firmware_module
from trezorlib._internal import firmware_headers


def sign_release(manifest_path: Path, release_dir: Path, out: Path) -> None:
    doc = json.loads(manifest_path.read_text())
    models = firmware_module.manifest_models(doc, manifest_path)

    signatures: dict[str, dict] = {}
    for model, body in sorted(models.items()):
        # A bundle dir holds the members directly; a release keys by model.
        model_dir = release_dir if "models" not in doc else release_dir / model
        bl_path = model_dir / body["bootloader"]["file"]
        bl = firmware_headers.BootloaderV2Image.parse(bl_path.read_bytes())

        if bl.signature_present():
            raise SystemExit(
                f"{bl_path} is already signed -- prepare an unsigned release "
                f"first (`xtask release` without --bootloader-devel, or "
                f"`firmware_pq_sign.py --unsigned`)"
            )

        root = bl.merkle_root()
        recorded = body["bootloader"]["signed_root"]
        if root.hex() != recorded:
            raise SystemExit(
                f"{model}: the bootloader folds to {root.hex()[:16]}… but the "
                f"manifest records {recorded[:16]}… -- the release is "
                f"inconsistent, re-prepare it"
            )

        # sign_with_devkeys sets sigmask; if prepare committed a different one
        # the (authenticated) digest moves and the signature would not cover it.
        bl.sign_with_devkeys()
        if bl.merkle_root() != root:
            raise SystemExit(
                f"{model}: signing changed the digest (sigmask 0x"
                f"{bl.header.sigmask:02x} is not what was prepared) -- the "
                "signature would not cover the prepared release"
            )

        signatures[model] = {
            "model_root": root.hex(),
            "sigmask": bl.header.sigmask,
            "slh": [bytes(s).hex() for s in bl.unauth.slh_signatures],
            "ec": [bytes(s).hex() for s in bl.unauth.ec_signatures],
        }
        print(f"signed {model:8} modelRoot {root.hex()[:16]}… (devel keys)")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "format": f"{firmware_module.BUNDLE_MAGIC}-sig",
                "format_version": firmware_module.FORMAT_VERSION,
                "key_set": "devel",
                "models": signatures,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"signatures     : {out}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="the prepared release's manifest (release[_devel].json) or one "
        "model's bundle.json. Passed rather than guessed, because a devel "
        "release manifest is named release_devel.json.",
    )
    ap.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="the directory the manifest describes: holding one bundle "
        "subdirectory per model for a release, or the members directly for "
        "one bundle",
    )
    ap.add_argument(
        "--out", type=Path, required=True, help="signature set to write (JSON)"
    )
    args = ap.parse_args()
    sign_release(args.manifest, args.dir, args.out)


if __name__ == "__main__":
    main()
