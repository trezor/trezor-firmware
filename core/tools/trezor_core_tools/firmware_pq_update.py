#!/usr/bin/env python3
"""Prototype orchestrator for a Merkle-tree (pq_secure_boot) OTA update.

Drives the two-phase device flow against a connected Trezor in bootloader mode:

    phase 1   FirmwareBegin (new signed boot header + the firmware's module
              headers) -> the device authenticates, confirms, decides keep-seed,
              stages the boot header via the UCB and reboots
    <reboot>  the boardloader installs the new boot header; the freshly booted
              bootloader enters auto-update (BOOT_COMMAND_INSTALL_UPGRADE)
    phase 2   FirmwareErase + stream firmware.bin -> modules written to the
              firmware area and verified as a tree against the new firmware_root

Inputs are the built artifacts: bootloader.bin (the new signed boot header sits
at its start) and firmware.bin (the [secmon | kernel+coreapp] tree image).

PROTOTYPE: header-only phase 1 only (the bootloader *code* is assumed unchanged;
the device rejects a code change on this path for now). The reconnect across the
reboot is best-effort. Needs a device or emulator to exercise end-to-end.
"""

from __future__ import annotations

import argparse
import struct
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from trezor_core_tools import firmware_module

from trezorlib import firmware, messages
from trezorlib.client import Session, TrezorClient, get_default_client

# header_size is a uint32 at offset 28 of boot_header_auth_t (sec/boot_header.h:
# magic, hw_model, hw_revision, version[4], fix_version[4], min_prev_version[4],
# monotonic(1), sigmask(1), reserved[2], header_size).
_HEADER_SIZE_OFFSET = 28


def boot_header_bytes(bootloader_bin: bytes) -> bytes:
    """The boot header (header_size bytes) at the start of a bootloader image."""
    (header_size,) = struct.unpack_from("<I", bootloader_bin, _HEADER_SIZE_OFFSET)
    if header_size == 0 or header_size > len(bootloader_bin):
        raise SystemExit(f"bad bootloader header_size: {header_size}")
    return bootloader_bin[:header_size]


def _button_callback(br: "messages.ButtonRequest") -> None:
    print("  -> confirm the action on the device")


def connect(retries: int = 1, delay: float = 1.0) -> tuple[TrezorClient, Session]:
    """Open a session to a connected device, retrying while it (re)enumerates."""
    last: Exception | None = None
    for _ in range(retries):
        try:
            client = get_default_client(
                "firmware_pq_update", button_callback=_button_callback
            )
            return client, client.get_session(passphrase=None)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay)
    raise SystemExit(f"could not connect to device: {last}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--bootloader",
        type=Path,
        help="bootloader.bin (its boot header carries the firmware_root)",
    )
    ap.add_argument(
        "--firmware",
        type=Path,
        help="firmware.bin (the [secmon|kernel+coreapp] tree image)",
    )
    ap.add_argument(
        "--bundle",
        type=Path,
        help="a build_firmware_pq bundle -- either the output DIR or the "
        "portable .zip; with --variant, resolves "
        "--bootloader/--firmware from it",
    )
    ap.add_argument(
        "--variant", help="variant name within --bundle to upload (e.g. universal)"
    )
    ap.add_argument(
        "--skip-check",
        action="store_true",
        help="skip the pre-upload consistency guard (not recommended)",
    )
    ap.add_argument("--reconnect-retries", type=int, default=30)
    args = ap.parse_args()

    # Resolve paths from a bundle (--bundle DIR|ZIP --variant NAME) or take them
    # directly. A .zip is extracted to a temp dir kept alive for the whole run
    # (_bundle_tmp), so the <variant>.bin + its .proof are on disk when read below.
    _bundle_tmp: tempfile.TemporaryDirectory | None = None
    if args.bundle is not None:
        if not args.variant:
            raise SystemExit("--bundle requires --variant (e.g. --variant universal)")
        bundle_dir = args.bundle
        if args.bundle.is_file() and zipfile.is_zipfile(args.bundle):
            _bundle_tmp = tempfile.TemporaryDirectory(prefix="fwtree-bundle-")
            with zipfile.ZipFile(args.bundle) as zf:
                zf.extractall(_bundle_tmp.name)
            bundle_dir = Path(_bundle_tmp.name)
        args.bootloader = args.bootloader or bundle_dir / "bootloader.bin"
        args.firmware = args.firmware or bundle_dir / f"{args.variant}.bin"
    if args.bootloader is None or args.firmware is None:
        raise SystemExit("need --bootloader + --firmware, or --bundle + --variant")

    # --- Pre-upload guard: refuse to OTA an unsigned bootloader or a variant whose
    #     proof does not fold to its firmware_root (reuses the build-time guard). The
    #     unauth-proof/flash-target check does NOT apply here -- phase 1 rewrites the
    #     unauth proof from the wire. ---
    if not args.skip_check:
        from trezor_core_tools.build_firmware_pq import (
            check_signed_bootloader,
            check_variant_folds,
        )

        root, _bl, problems = check_signed_bootloader(args.bootloader)
        # Every variant -- including the custom slot -- folds to firmware_root
        # (variant_leaf zeroes the custom app hash in the authenticity leaf), so
        # the variant-fold guard always applies.
        if root is not None:
            problems += check_variant_folds(args.firmware, root)
        if problems:
            print("PRE-UPLOAD CHECK FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            raise SystemExit("refusing to upload (override with --skip-check)")

    bl = args.bootloader.read_bytes()
    fw = args.firmware.read_bytes()

    boot_header = boot_header_bytes(bl)
    # Always make the bootloader code (everything after the boot header) available.
    # The DEVICE decides whether to stream it: if its current code already conforms
    # to the new header it does a header-only update and never requests the code;
    # otherwise it requests + streams the full code. No host-side --full-bootloader
    # guess -- the device is the judge.
    bl_code = bl[len(boot_header) :]
    mods = firmware_module.manifest_entries(fw)
    # Preamble blob = [manifest || firmware_proof]. The proof (co-path variant leaf
    # -> firmware_root) is written next to the firmware by the signer as
    # `<firmware>.proof`; empty for a single-variant firmware.
    manifest = firmware_module.read_manifest(fw)
    proof_path = args.firmware.with_suffix(args.firmware.suffix + ".proof")
    proof = proof_path.read_bytes() if proof_path.exists() else b""
    module_headers = manifest + proof
    names = [firmware_module.TYPE_NAMES.get(m["module_type"], "?") for m in mods]
    # Custom (unofficial) is the authenticated FW_VARIANT_CUSTOM variant; the
    # device derives + gates it (unlocked bootloader, unprivileged). Detected here
    # only to annotate the output -- there is no host flag to send.
    is_custom = firmware_module.is_custom_firmware(fw)
    mode = f"bl code available ({len(bl_code)} B); device decides header-only vs full"
    if is_custom:
        mode += " [CUSTOM/unofficial]"
    print(
        f"boot header: {len(boot_header)} B | manifest: {len(manifest)} B | "
        f"proof: {len(proof)} B ({len(proof) // 32} nodes) | modules: {names} | "
        f"phase-1: {mode}"
    )

    # --- Phase 1 ---
    print(f"phase 1: FirmwareBegin ({mode}) ...")
    _client, session = connect()
    if session.features.bootloader_mode is not True:
        raise SystemExit("device must be in bootloader mode")
    streamed = firmware.firmware_begin(
        session, boot_header, module_headers, code=bl_code
    )
    print(
        f"phase 1 done ({'full bootloader streamed' if streamed else 'header-only'} "
        "-- device's choice); device is rebooting to install the bootloader ..."
    )

    # --- Reconnect across the boardloader-mediated reboot ---
    time.sleep(3)
    _client, session = connect(retries=args.reconnect_retries)
    print("reconnected in bootloader mode; phase 2: streaming firmware ...")

    # --- Phase 2 (reuses the standard firmware upload; device installs modules) ---
    firmware.update(session, fw)
    print("phase 2 done; firmware installed.")


if __name__ == "__main__":
    main()
