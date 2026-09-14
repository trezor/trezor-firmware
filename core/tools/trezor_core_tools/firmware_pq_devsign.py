#!/usr/bin/env python3
"""Sign a PREPARED release with development keys -- the ceremony's stand-in.

This is the middle stage of the release flow, and the ONLY one that touches a
key::

    prepare   build every model, fold every tree, leave signatures zero
    sign      32 bytes per model in, two hybrid signature pairs per model out
    attach    patch those signatures into the prepared artifacts

A real release replaces this stage with an airgapped ceremony. Everything the
signer needs is already in the prepared container -- each model records the
`modelRoot` its boot header commits to, and the header carries the `sigmask`
naming the key slots -- so there is no separate request format to keep in step
with the release. The container IS the request.

What comes back is a signature set per model, which `firmware_pq_attach.py`
patches in. Signatures land in UNAUTHENTICATED space (the boot header's unauth
region, the nRF's unprotected TLVs), so attaching them changes no digest and
cannot invalidate anything prepared earlier.

The signing input is read from the prepared BOOTLOADER, not from the container's
recorded value: the bootloader is what the device authenticates, so signing what
it actually folds to removes any chance of signing a number that merely sits
beside it. The two are cross-checked, and a disagreement is fatal.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trezor_core_tools import firmware_module
from trezorlib._internal import firmware_headers


def sign_release(bundle_path: Path, tree_dir: Path, out: Path) -> None:
    doc = json.loads(bundle_path.read_text())
    models = firmware_module.container_models(doc, bundle_path)

    signatures: dict[str, dict] = {}
    for model, body in sorted(models.items()):
        # A per-model release directory holds the members directly; a tree of
        # them keys by model.
        model_dir = tree_dir if "models" not in doc else tree_dir / model
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
                f"container records {recorded[:16]}… -- the release is "
                f"inconsistent, re-prepare it"
            )

        # `sign_with_devkeys` sets sigmask to the development selection. If
        # prepare committed a DIFFERENT selection -- a production one -- that
        # write moves an authenticated field and the digest with it, so the
        # signature would not cover what was prepared. Caught here rather than
        # discovered on a device.
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
                "format": f"{firmware_module.CONTAINER_MAGIC}-sig",
                "format_version": firmware_module.CONTAINER_VERSION,
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
        "--bundle",
        type=Path,
        required=True,
        help="the prepared release's manifest: a cross-model set "
        "(bundle[_devel].json) or one model's bundle.json. Passed rather than "
        "guessed, because a devel set is named bundle_devel.json.",
    )
    ap.add_argument(
        "--tree",
        type=Path,
        required=True,
        help="the directory the manifest describes: holding one subdirectory "
        "per model for a set, or the members directly for one model",
    )
    ap.add_argument(
        "--out", type=Path, required=True, help="signature set to write (JSON)"
    )
    args = ap.parse_args()
    sign_release(args.bundle, args.tree, args.out)


if __name__ == "__main__":
    main()
