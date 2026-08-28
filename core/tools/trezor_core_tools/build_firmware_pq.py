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
folds the founder firmware_root in and re-signs it, and bakes each variant's proof
into its firmware.bin -- then runs a consistency GUARD over the result so it can
never hand you a mismatched pair. Each firmware.bin is self-contained (its Merkle
proof rides in the manifest region), so the output directory is a ready-to-OTA
bundle.

By default the bootloader is left BARE (firmware_type=0), so the firmware must be
installed via OTA (which stamps firmware_type; the proof rides in the image). Pass
--flash-target <variant> to instead stamp that variant's firmware_type into the
bootloader for direct flashing (a combined ready-to-flash image is deferred).

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
# custom adds --unsafe-fw => FW_VARIANT_CUSTOM: the founder-signed unofficial-app
# slot. Its leaf zeroes the app version/size/code_hash, so this one build
# establishes a slot that ANY creator app folds to (installed unprivileged,
# unlocked-bootloader-only, own storage domain). Shipping it in the bundle is a
# deliberate product choice -- custom firmware is allowed on production devices.
VARIANT_FLAGS: dict[str, list[str]] = {
    "universal": [],
    "btc-only": ["--btc-only"],
    "custom": ["--unsafe-fw"],
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
DEFAULT_VARIANTS = ["universal", "btc-only", "custom", "prodtest"]


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
    dbg_console: str | None = None,
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
    #   --dbg-console     : debug console backend, for the boot/Python log output.
    #                       Forwarded to every build so the bootloader, the
    #                       variants AND the secmon each get the same backend --
    #                       the secmon is where the privileged side of
    #                       dbg_console_write lives, so a firmware built without
    #                       it logs into a no-op.
    flags: list[str] = []
    if production:
        flags.append("--production")
    if bootloader_devel:
        flags.append("--bootloader-devel")
    if dbg_console:
        flags += ["--dbg-console", dbg_console]

    # Bootloader (firmware_root is a 0 placeholder until we sign).
    print(f"building bootloader ({model}) ...")
    _run_xtask("build", "bootloader", "--model", model, *flags)
    _collect("bootloader.bin", output / "bootloader.bin")

    # One image per variant (artifacts/latest/{firmware,prodtest}.bin is overwritten
    # by each build, so copy it to <variant>.bin right after). Prodtest is its own
    # project (a single secure module). The custom variant is just another firmware
    # build with VARIANT_FLAGS["custom"] == --unsafe-fw (=> FW_VARIANT_CUSTOM).
    for v in variants:
        if v == PRODTEST_VARIANT:
            print(f"building prodtest ({model}) ...")
            _run_xtask("build", "prodtest", "--model", model, *flags)
            _collect("prodtest.bin", output / f"{v}.bin")
        else:
            note = " [CUSTOM/unofficial slot]" if v == "custom" else ""
            print(f"building firmware variant '{v}' ({model}){note} ...")
            _run_xtask("build", "firmware", "--model", model, *VARIANT_FLAGS[v], *flags)
            _collect("firmware.bin", output / f"{v}.bin")


def sign(
    output: Path,
    variants: list[str],
    flash_target: str | None,
    nrf: Path | None = None,
    nrf_pq_native: bool = False,
) -> None:
    """Fold the founder firmware_root over all variants into the bootloader, re-sign,
    and bake each variant's proof into its firmware.bin. By default the bootloader is
    left BARE (firmware_type=0) so firmware must be installed via OTA; with a
    flash_target, that variant's firmware_type is stamped in for direct-flashing.
    With `nrf`, the nRF image is committed as a model-tree leaf under the same
    signature and its OTA co-path/hash are recorded in bundle.json."""
    cmd = [sys.executable, str(SIGNER)]
    for v in variants:
        cmd += ["--firmware", str(output / f"{v}.bin")]
    cmd += [
        "--bootloader",
        str(output / "bootloader.bin"),
        "--manifest-out",
        str(output / "bundle.json"),
    ]
    if nrf is not None:
        cmd += ["--nrf", str(nrf)]
        if nrf_pq_native:
            cmd += ["--nrf-pq-native"]
    if flash_target is None:
        cmd += ["--bare"]
    else:
        cmd += ["--install-proof", str(output / f"{flash_target}.bin")]
    print("signing bundle ...")
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


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
    """A variant's leaf, folded through the proof baked into its image, must equal
    the signed firmware_root. This is the tie between a variant image and a
    bootloader."""
    if not fw_path.exists():
        return [f"firmware missing ({fw_path})"]
    fw = fw_path.read_bytes()
    leaf = firmware_module.variant_leaf(firmware_module.read_manifest(fw))
    proof = firmware_module.read_manifest_proof(fw)
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
    firmware_root, and -- depending on mode -- a bootloader whose firmware_type is
    not bare (OTA-only) or not stamped to the flash-target variant (direct-flash).
    """
    root, bl, problems = check_signed_bootloader(output / "bootloader.bin")
    if root is None or bl is None:
        return problems

    # Every variant leaf must fold through the proof baked into its image to the
    # signed firmware_root.
    for v in variants:
        problems += check_variant_folds(output / f"{v}.bin", root)

    # The proof rides in each firmware image (checked above); the bootloader only
    # carries firmware_type. Bare -> firmware_type 0 (OTA stamps it); flash-target
    # -> firmware_type stamped to that variant so a direct-flashed device boots.
    if flash_target is None:
        if bl.unauth.firmware_type != 0:
            problems.append(
                f"bootloader firmware_type={bl.unauth.firmware_type} != 0 -- "
                "expected a bare (unprovisioned) bootloader for OTA-only"
            )
    else:
        tgt = output / f"{flash_target}.bin"
        if tgt.exists():
            tgt_variant = firmware_module.manifest_variant(
                firmware_module.read_manifest(tgt.read_bytes())
            )
            if bl.unauth.firmware_type != tgt_variant:
                problems.append(
                    f"stamped firmware_type={bl.unauth.firmware_type} != flash-target "
                    f"'{flash_target}' variant {tgt_variant} -- direct-flashed device "
                    "would read as unprovisioned (empty)"
                )
    return problems


def default_nrf_image(model: str, bootloader_devel: bool) -> Path | None:
    """The committed nRF MCUboot image for this model, matching what the coreapp
    would embed (firmware/build.rs: trezor-ble{-dev}.bin). None if absent."""
    suffix = "-dev" if bootloader_devel else ""
    path = CORE / "embed" / "models" / model / f"trezor-ble{suffix}.bin"
    return path if path.exists() else None


def warn_if_nrf_stale(committed: Path) -> None:
    """Warn when a FRESHER nRF build is sitting in nordic/ unstaged.

    The committed image is what gets signed as the model-tree leaf and embedded in
    the coreapp. Building the nRF does NOT update it -- build_sign_flash.sh -d -s
    does the copy -- so it is entirely possible to sign a leaf that is weeks older
    than the image you just built, with nothing to tell you. That silence has
    already cost a debugging session, hence this check.
    """
    built = (
        CORE.parent
        / "nordic"
        / "trezor"
        / "build"
        / "trezor-ble"
        / "zephyr"
        / "zephyr.trz.bin"
    )
    try:
        if not built.exists():
            return
        b, c = built.stat().st_mtime, committed.stat().st_mtime
        if b <= c:
            return
    except OSError:
        return
    from datetime import datetime as _dt

    fmt = "%Y-%m-%d %H:%M"
    print(
        f"WARNING: a newer nRF build exists but was never staged:\n"
        f"    built    {_dt.fromtimestamp(b).strftime(fmt)}  {built}\n"
        f"    signing  {_dt.fromtimestamp(c).strftime(fmt)}  {committed}\n"
        f"  The tree leaf and the embedded coreapp image will both be the OLDER\n"
        f"  one. To stage the fresh build, re-run the nRF build with -d -s\n"
        f"  (build_sign_flash.sh), or pass --nrf <path> to use it for the tree only."
    )


def zip_bundle(output: Path, variants: list[str], nrf_name: str | None = None) -> Path:
    """Pack the bundle into a single portable <name>.zip (flat: bootloader.bin, each
    <variant>.bin, bundle.json, and the nRF image if present). Each <variant>.bin is
    self-contained (its Merkle proof is baked into the manifest region).
    firmware_pq_update.py accepts this zip directly via `--bundle <zip> --variant
    <name>` (it extracts to a temp dir)."""
    zip_path = output.parent / f"{output.name}.zip"
    files = [output / "bootloader.bin", output / "bundle.json"]
    for v in variants:
        files.append(output / f"{v}.bin")
    if nrf_name is not None:
        files.append(output / nrf_name)
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
    nrf_name: str | None = None,
) -> None:
    rel = output.relative_to(CORE) if output.is_relative_to(CORE) else output
    print(f"\nbundle OK -> {rel}/")
    bare = flash_target is None
    print(
        "  bootloader.bin        "
        + (
            "(BARE: firmware_type=0 -> OTA only)"
            if bare
            else f"(direct-flash: firmware_type={flash_target})"
        )
    )
    for v in variants:
        print(f"  {v}.bin  (proof baked in)")
    if nrf_name is not None:
        print(f"  {nrf_name}  (nRF leaf; co-path in bundle.json)")
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
        help="stamp THIS variant's firmware_type into the bootloader for direct "
        "flashing (default: none -> BARE bootloader; install firmware via OTA)",
    )
    ap.add_argument(
        "--nrf",
        type=Path,
        help="signed nRF MCUboot image to commit as a model-tree leaf + include in "
        "the OTA bundle (default: the model's committed trezor-ble{-dev}.bin)",
    )
    ap.add_argument(
        "--nrf-pq-native",
        action="store_true",
        help="build the nRF image as PQ-NATIVE (founder signature + co-path embedded "
        "in its TLVs, verified by its own MCUboot). Needs an nRF bootloader built "
        "with CONFIG_BOOT_FOUNDER_TREE=y.",
    )
    ap.add_argument(
        "--no-nrf",
        action="store_true",
        help="do not include the nRF image (single-leaf bootloader signing)",
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
    # Only the backends EVERY project in this bundle supports: prodtest and secmon
    # declare swo/system-view but not vcp (see their project.toml), and the flag is
    # forwarded to all of them.
    ap.add_argument(
        "--dbg-console",
        choices=["swo", "system-view"],
        default=None,
        help="enable the debug console on this backend (default: off). 'swo' "
        "prints over SWO/ITM port 0 -- the coreapp boot log and, unfiltered, the "
        "MicroPython traceback",
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

    # Resolve the nRF image: explicit --nrf, else the model's committed image
    # (matching what the coreapp embeds), unless --no-nrf. Copied into the bundle
    # under its own name so bundle.json's "image" ref + the zip are self-contained.
    nrf_src: Path | None = None
    if not args.no_nrf:
        nrf_src = args.nrf or default_nrf_image(args.model, args.bootloader_devel)
        if args.nrf and not args.nrf.exists():
            raise SystemExit(f"--nrf {args.nrf}: not found")
        # Only meaningful for the committed image: an explicit --nrf is the caller
        # saying which one they want.
        if nrf_src is not None and not args.nrf:
            warn_if_nrf_stale(nrf_src)
    nrf_in_bundle: Path | None = None
    nrf_name: str | None = None

    if not args.check_only:
        if not args.skip_build:
            build(
                args.model,
                variants,
                output,
                args.production,
                args.bootloader_devel,
                args.dbg_console,
            )
        if nrf_src is not None:
            nrf_name = nrf_src.name
            nrf_in_bundle = output / nrf_name
            # Pad the bundle copy to the flash write block (16 B on U5): the OTA
            # upload engine requires a flash-aligned image size, but an MCUboot
            # image is an arbitrary length. MCUboot reads by its header sizes and
            # ignores trailing bytes, so the padding is inert for the nRF. It is
            # also outside the model-tree leaf, which covers only MCUboot's signed
            # region (nrf_tree.nrf_leaf), so the fold is independent of how the
            # image is padded. Copied (not padded in place) so the committed source
            # is never modified.
            raw = nrf_src.read_bytes()
            nrf_in_bundle.write_bytes(raw + b"\x00" * ((-len(raw)) % 16))
        sign(output, variants, flash_target, nrf_in_bundle, args.nrf_pq_native)
    elif nrf_src is not None:
        # check-only: the image was copied into the bundle by a prior run
        nrf_name = nrf_src.name
        if not (output / nrf_name).exists():
            nrf_name = None

    problems = check(output, variants, flash_target)
    if problems:
        print("\nBUNDLE CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        raise SystemExit(1)
    archive = zip_bundle(output, variants, nrf_name)
    _summary(output, variants, flash_target, archive, nrf_name)


if __name__ == "__main__":
    main()
