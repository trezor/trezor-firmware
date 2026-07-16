#!/usr/bin/env python3
"""Build + sign a Merkle-tree (pq_secure_boot) firmware bundle in ONE command.

This replaces the error-prone manual dance:

    xtask build bootloader --model M --bootloader-devel      # firmware_root = 0 !
    xtask build firmware   --model M                         # -> firmware.bin
    cp .../firmware.bin universal.bin                        # (artifacts/latest
    xtask build firmware   --model M --btc-only              #  is overwritten each
    cp .../firmware.bin btconly.bin                          #  build, so copy aside)
    firmware_pq_sign.py --firmware universal.bin --firmware btconly.bin \
        --bootloader bootloader.bin --install-proof universal.bin

...and every one of those steps has bitten us: forgetting to copy a variant aside,
flashing the firmware_root=0 bootloader from step 1 instead of the re-signed one, or
forgetting --install-proof for a direct flash -> "firmware corrupted" on the device.

This tool builds each requested variant into its own file, builds the bootloader,
folds the founder firmware_root in and re-signs it, and writes each variant's proof
-- then runs a consistency GUARD over the result so it can never hand you a
mismatched pair. The output directory is a self-contained, ready-to-OTA bundle.

By default the bootloader is left BARE (variant=0, no proof in the unauth region),
so the firmware must be installed via OTA (which writes the variant + proof into the
boot header). Pass --flash-target <variant> to instead bake that variant's proof into
the bootloader for direct flashing (a combined ready-to-flash image is deferred).

DEV ONLY for now: signing uses dev keys (firmware_pq_sign -> sign_with_devkeys).
Production founder-key signing is deferred (#12).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from trezor_core_tools import firmware_module

from trezorlib._internal import firmware_headers

_HERE = Path(__file__).resolve()
CORE = _HERE.parents[2]
EMBED = CORE / "embed"
LATEST = CORE / "build-xtask" / "artifacts" / "latest"
SIGNER = _HERE.with_name("firmware_pq_sign.py")

# Variant name -> extra `xtask build firmware` flags. universal is the default
# build; bitcoin-only adds --btc-only (feature_resolver: !btc_only => universal_fw).
VARIANT_FLAGS: dict[str, list[str]] = {
    "universal": [],
    "btc-only": ["--btc-only"],
}
# Prodtest is its OWN project (`xtask build prodtest`), a single secure module --
# not a firmware variant -- but it folds into the founder firmware_root as another
# variant leaf (FW_VARIANT_PRODTEST=4).
# NOTE (deferred #29): prodtest is a maximally-privileged, founder-signed, secure-
# world image with provisioning_access. Folding it into the DEFAULT bundle means the
# shipped/field bootloader's firmware_root trusts it, so a founder-signed prodtest is
# installable on any field device (official firmware installs without unlock) -- a
# "skeleton key". Accepted FOR NOW to keep the factory flow simple; revisit before
# production signing (unlock-gate the prodtest install, or factory-lock
# provisioning_access). Drop it from a bundle with `--variant universal --variant
# btc-only` (no prodtest).
PRODTEST_VARIANT = "prodtest"
ALL_VARIANTS = [*VARIANT_FLAGS, PRODTEST_VARIANT]
DEFAULT_VARIANTS = ["universal", "btc-only", "prodtest"]


def _run_xtask(*xargs: str) -> None:
    cmd = ["cargo", "xtask", *xargs]
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=EMBED, check=True)


def _collect(name: str, dst: Path) -> Path:
    """Copy a just-built artifact out of artifacts/latest before it is overwritten."""
    src = LATEST / name
    if not src.exists():
        raise SystemExit(f"expected build artifact missing: {src}")
    shutil.copy2(src, dst)
    return dst


def build(
    model: str,
    variants: list[str],
    output: Path,
    production: bool,
    bootloader_devel: bool,
    unsafe_fw: bool = False,
) -> None:
    output.mkdir(parents=True, exist_ok=True)

    # Two INDEPENDENT axes, both forwarded verbatim to every build:
    #   --production      : build settings / feature set (feature_resolver).
    #   --bootloader-devel: key selection (dev vs prod keys) + dev bootloader
    #                       features + which secmon the kernel embeds.
    # IMPORTANT: --bootloader-devel must reach the FIRMWARE build, not just the
    # bootloader -- kernel/build.rs only embeds the freshly-built OUT_DIR secmon
    # under `bootloader_devel`; otherwise the kernel links against a different
    # (committed/stale) secmon than the one prefixed into firmware.bin, so its
    # secure-gateway veneer is offset and the kernel SecureFaults the instant it
    # runs. Bootloader + firmware must therefore share the same flags.
    flags: list[str] = []
    if production:
        flags.append("--production")
    if bootloader_devel:
        flags.append("--bootloader-devel")

    # Bootloader (firmware_root is a 0 placeholder until we sign).
    print(f"building bootloader ({model}) ...")
    _run_xtask("build", "bootloader", "--model", model, *flags)
    _collect("bootloader.bin", output / "bootloader.bin")

    # --unsafe-fw zeroes each variant manifest's kernel+coreapp hash -> a CUSTOM
    # (unofficial) bundle where any kernel+coreapp installs as custom. Applied to
    # the firmware builds only (the bootloader has no firmware manifest).
    fw_flags = flags + (["--unsafe-fw"] if unsafe_fw else [])

    # One image per variant (artifacts/latest/{firmware,prodtest}.bin is overwritten
    # by each build, so copy it to <variant>.bin right after). Prodtest is its own
    # project (a single secure module, never custom -> no --unsafe-fw).
    for v in variants:
        if v == PRODTEST_VARIANT:
            print(f"building prodtest ({model}) ...")
            _run_xtask("build", "prodtest", "--model", model, *flags)
            _collect("prodtest.bin", output / f"{v}.bin")
        else:
            print(
                f"building firmware variant '{v}' ({model}) "
                f"{'[CUSTOM/unsafe]' if unsafe_fw else ''}..."
            )
            _run_xtask(
                "build", "firmware", "--model", model, *VARIANT_FLAGS[v], *fw_flags
            )
            _collect("firmware.bin", output / f"{v}.bin")


def sign(output: Path, variants: list[str], flash_target: str | None) -> None:
    """Fold the founder firmware_root over all variants into the bootloader, re-sign,
    and write each variant's proof. By default the bootloader is left BARE (variant=0,
    no proof) so firmware must be installed via OTA; with a flash_target, that
    variant's proof is installed into the unauth region for direct-flashing."""
    cmd = [sys.executable, str(SIGNER)]
    for v in variants:
        cmd += ["--firmware", str(output / f"{v}.bin")]
    cmd += [
        "--bootloader",
        str(output / "bootloader.bin"),
        "--manifest-out",
        str(output / "bundle.json"),
    ]
    if flash_target is None:
        cmd += ["--bare"]
    else:
        cmd += ["--install-proof", str(output / f"{flash_target}.bin")]
    print("signing bundle ...")
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _proof_nodes(path: Path) -> list[bytes]:
    data = path.read_bytes() if path.exists() else b""
    return [data[i : i + 32] for i in range(0, len(data), 32)]


def check_signed_bootloader(
    bl_path: Path,
) -> tuple[bytes | None, firmware_headers.BootloaderV2Image | None, list[str]]:
    """Parse the bootloader; return (firmware_root, bl, problems). firmware_root is
    None if the bootloader is missing/unreadable. Reusable by any pre-flash/pre-OTA
    check -- flags an unsigned (root=0) bootloader or a bad signature."""
    if not bl_path.exists():
        return None, None, [f"bootloader missing: {bl_path}"]
    bl = firmware_headers.BootloaderV2Image.parse(bl_path.read_bytes())
    root = bytes(bl.header.firmware_root)
    problems: list[str] = []
    if root == b"\x00" * 32:
        problems.append(
            "bootloader firmware_root is ZERO -- not tree-signed (re-run signing; "
            "do NOT flash/upload this bootloader)"
        )
    try:
        bl.verify(dev_keys=True)
    except Exception as e:  # noqa: BLE001
        problems.append(f"bootloader signature invalid: {e}")
    return root, bl, problems


def check_variant_folds(fw_path: Path, root: bytes) -> list[str]:
    """A variant's leaf, folded through its sibling `.proof`, must equal the signed
    firmware_root. This is the tie between a variant image and a bootloader."""
    if not fw_path.exists():
        return [f"firmware missing ({fw_path})"]
    leaf = firmware_module.variant_leaf(
        firmware_module.read_manifest(fw_path.read_bytes())
    )
    proof = _proof_nodes(fw_path.with_suffix(".bin.proof"))
    folded = firmware_module._fold_proof(leaf, proof)
    if folded != root:
        return [
            f"{fw_path.name}: leaf+proof folds to {folded.hex()[:12]}, not "
            f"firmware_root {root.hex()[:12]}"
        ]
    return []


def check(output: Path, variants: list[str], flash_target: str | None) -> list[str]:
    """Consistency guard: prove the bundle is self-consistent BEFORE it is flashed.

    Catches every mismatch class we have hit: an unsigned (root=0) bootloader, a
    bad signature, a variant whose leaf+proof does not fold to the signed
    firmware_root, and -- depending on mode -- either a non-bare bootloader (when we
    want OTA-only) or a flash-target whose proof was not installed (direct-flash).
    """
    root, bl, problems = check_signed_bootloader(output / "bootloader.bin")
    if root is None or bl is None:
        return problems

    # Every variant leaf must fold through its proof to the signed firmware_root.
    for v in variants:
        problems += check_variant_folds(output / f"{v}.bin", root)

    # firmware_proof_* are absent (None) on non-pq bootloaders (see core.py); a pq
    # bootloader always has them, but guard for the type checker + non-pq bins.
    installed = [bytes(n) for n in (bl.unauth.firmware_proof_nodes or [])][
        : bl.unauth.firmware_proof_count or 0
    ]
    if flash_target is None:
        # Bare bootloader: unauth must carry no variant and no proof, so firmware
        # can only be installed via OTA (which writes them from the wire).
        if bl.unauth.firmware_proof_count != 0 or installed:
            problems.append(
                f"bootloader unauth is not bare ({len(installed)} proof node(s)) -- "
                "expected variant=0 / no proof for the OTA-only bootloader"
            )
        if bl.unauth.firmware_type != 0:
            problems.append(
                f"bootloader unauth firmware_type={bl.unauth.firmware_type} != 0 -- "
                "expected a bare (unprovisioned) bootloader"
            )
    else:
        # The flash-target's proof AND variant must be installed in the bootloader
        # unauth (direct-flash only; an OTA rewrites both from the wire): the proof
        # so the variant leaf folds to firmware_root, and firmware_type so the
        # device reads as provisioned (fw_check keys off firmware_type != 0).
        tgt = output / f"{flash_target}.bin"
        tgt_proof = _proof_nodes(tgt.with_suffix(".bin.proof"))
        if installed != tgt_proof:
            problems.append(
                f"installed unauth proof ({len(installed)} nodes) != flash-target "
                f"'{flash_target}' proof ({len(tgt_proof)} nodes) -- direct-flashing "
                f"'{flash_target}' would not boot"
            )
        if tgt.exists():
            tgt_variant = firmware_module.manifest_variant(
                firmware_module.read_manifest(tgt.read_bytes())
            )
            if bl.unauth.firmware_type != tgt_variant:
                problems.append(
                    f"installed firmware_type={bl.unauth.firmware_type} != flash-target "
                    f"'{flash_target}' variant {tgt_variant} -- direct-flashed device "
                    "would read as unprovisioned (empty)"
                )
    return problems


def zip_bundle(output: Path, variants: list[str]) -> Path:
    """Pack the bundle into a single portable <name>.zip (flat: bootloader.bin, each
    <variant>.bin + its .proof, bundle.json). firmware_pq_update.py accepts this zip
    directly via `--bundle <zip> --variant <name>` (it extracts to a temp dir)."""
    zip_path = output.parent / f"{output.name}.zip"
    files = [output / "bootloader.bin", output / "bundle.json"]
    for v in variants:
        files.append(output / f"{v}.bin")
        files.append(output / f"{v}.bin.proof")  # may be empty for a single variant
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.exists():
                zf.write(f, arcname=f.name)
    return zip_path


def _summary(
    output: Path,
    variants: list[str],
    flash_target: str | None,
    archive: Path | None = None,
) -> None:
    rel = output.relative_to(CORE) if output.is_relative_to(CORE) else output
    print(f"\nbundle OK -> {rel}/")
    bare = flash_target is None
    print(
        "  bootloader.bin        "
        + (
            "(BARE: variant=0 / no proof -> OTA only)"
            if bare
            else f"(direct-flash proof: {flash_target})"
        )
    )
    for v in variants:
        print(f"  {v}.bin  +  {v}.bin.proof")
    print("  bundle.json")
    if archive is not None:
        arel = archive.relative_to(CORE) if archive.is_relative_to(CORE) else archive
        print(f"\nportable bundle -> {arel}  (single file for OTA)")
    print("\nnext:")
    if not bare:
        print(f"  direct-flash : bootloader.bin + {flash_target}.bin")
    else:
        print("  direct-flash : bootloader.bin  (bare; firmware must come via OTA)")
    ota_src = (
        f"--bundle {arel} --variant <variant>"
        if archive is not None
        else f"--bootloader {rel}/bootloader.bin --firmware {rel}/<variant>.bin"
    )
    print(
        "  OTA          : python tools/trezor_core_tools/firmware_pq_update.py \\\n"
        f"                     {ota_src}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--model", required=True, help="e.g. T3W1")
    ap.add_argument(
        "--variant",
        action="append",
        choices=sorted(ALL_VARIANTS),
        help=f"repeatable; default: {' + '.join(DEFAULT_VARIANTS)}. "
        f"'{PRODTEST_VARIANT}' folds the factory-test image into the same tree.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        help="bundle dir (default: build-xtask/tree/<model>)",
    )
    ap.add_argument(
        "--flash-target",
        help="install THIS variant's proof+variant into the bootloader for direct "
        "flashing (default: none -> BARE bootloader; install firmware via OTA)",
    )
    # Two independent axes (do NOT conflate):
    #   --production      : build settings / feature set.
    #   --bootloader-devel: key selection (dev keys) + dev bootloader + which secmon
    #                       the kernel embeds. Default on for now (dev keys); the
    #                       signer only does dev keys, so production KEYS are blocked.
    ap.add_argument(
        "--production",
        action="store_true",
        help="production build settings (independent of key selection)",
    )
    ap.add_argument(
        "--bootloader-devel",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use dev keys + dev bootloader/secmon (default: on)",
    )
    ap.add_argument(
        "--unsafe-fw",
        action="store_true",
        help="build a CUSTOM/unofficial bundle: zero each manifest's kernel+coreapp "
        "hash so any kernel+coreapp installs as custom (unlocked-bootloader-only, "
        "boot warning, unprivileged). The secmon + manifest still conform/sign.",
    )
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="re-sign + check existing <output>/*.bin (skip the xtask builds)",
    )
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="only run the consistency guard over an existing bundle",
    )
    args = ap.parse_args()

    # xtask key selection: use_dev_keys = bootloader_devel || !production. Production
    # (founder-key) signing is not wired yet (deferred #12) and the signer only does
    # dev keys, so refuse a combination that would select production keys.
    if args.production and not args.bootloader_devel:
        raise SystemExit(
            "production (founder-key) signing is not wired yet (deferred #12); the "
            "signer only does dev keys. Keep --bootloader-devel (or drop --production)."
        )

    variants = args.variant or DEFAULT_VARIANTS
    output = args.output or (CORE / "build-xtask" / "tree" / args.model)
    # Default: no flash-target -> a bare bootloader (firmware installed via OTA).
    flash_target = args.flash_target
    if flash_target is not None and flash_target not in variants:
        raise SystemExit(f"--flash-target {flash_target} not among variants {variants}")

    if not args.check_only:
        if not args.skip_build:
            build(
                args.model,
                variants,
                output,
                args.production,
                args.bootloader_devel,
                args.unsafe_fw,
            )
        sign(output, variants, flash_target)

    problems = check(output, variants, flash_target)
    if problems:
        print("\nBUNDLE CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        raise SystemExit(1)
    archive = zip_bundle(output, variants)
    _summary(output, variants, flash_target, archive)


if __name__ == "__main__":
    main()
