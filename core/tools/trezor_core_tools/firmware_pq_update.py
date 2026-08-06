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

from trezorlib import exceptions, firmware, messages
from trezorlib.client import Session, TrezorClient, get_default_client

# TEST-ONLY fault injections -> expected device Failure substring. Phase-1 faults
# reject during FirmwareBegin; phase-2 faults reject during the streaming loop.
# `bl-sig` has no host Failure -- observe the device (boardloader RSOD on reboot).
_TAMPERS = {
    "fw-sig": "Firmware manifest not authentic",  # ph1: manifest byte -> fold != firmware_root
    # ph1: patch hw_model -> boot_header_auth_get rejects it ("Invalid boot header")
    # BEFORE the workflow's own (now-dead) "Wrong model" check.
    "wrong-model": "Invalid boot header",
    "variant-swap": "fold/authenticity failed",  # ph2: stream a different variant than ph1
    # ph2: flip a payload byte -> the chain check fails; on_chunk returns the
    # retryable status, so the device only fails terminally once the engine's
    # retry budget is exhausted -> "Invalid chunk hash".
    "corrupt-chunk": "Invalid chunk hash",
    # ph2: flip an inline prev_hash value -> same retry-then-fail path.
    "chunk-hash": "Invalid chunk hash",
    # ph2: drop an outer chunk's inline prev_hash -> terminal (no retry).
    "missing-chunk-hash": "missing chunk hash",
    # ph1 (CUSTOM variant only): inflate the app module size -- NOT founder-
    # authenticated for custom (zeroed-for-fold), so the manifest still folds, but
    # the layout check (fwt_manifest_layout_valid, run in phase 1 BEFORE confirm)
    # rejects a module that runs past the firmware area.
    "custom-app-size": "Invalid firmware manifest",
    # ph1: flip a boot-header sig byte -> forces the full-bootloader path; the
    # staging step (ucb_stage_commit) verifies the [header|code] sig and rejects.
    "bl-sig": "Invalid bootloader signature",
}


def _find_other_variant(fw_path: Path) -> Path:
    """A different variant's <name>.bin next to fw_path (for --tamper variant-swap)."""
    for p in sorted(fw_path.parent.glob("*.bin")):
        if p.name not in (fw_path.name, "bootloader.bin"):
            return p
    raise SystemExit("--tamper variant-swap needs a multi-variant bundle")


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
    ap.add_argument(
        "--tamper",
        choices=sorted(_TAMPERS),
        default=None,
        help="TEST ONLY: inject a fault to exercise a specific device rejection "
        "(each maps to an expected Failure; see _TAMPERS).",
    )
    ap.add_argument(
        "--tamper-offset",
        type=lambda x: int(x, 0),
        default=0x80000,
        help="byte offset for --tamper corrupt-chunk (default 0x80000, in the "
        "app module)",
    )
    ap.add_argument(
        "--expect-failure",
        default=None,
        help="TEST: exit 0 iff the device rejects with a Failure containing this "
        "substring (defaults to the --tamper case's expected message).",
    )
    args = ap.parse_args()

    # Resolve paths from a bundle (--bundle DIR|ZIP --variant NAME) or take them
    # directly. A .zip is extracted to a temp dir kept alive for the whole run
    # (_bundle_tmp), so the self-contained <variant>.bin (proof baked in) is on
    # disk when read below.
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
    # Preamble blob = the firmware image's manifest region [manifest || proof
    # struct] -- the exact bytes at the image start, since the signer bakes the
    # per-variant Merkle proof (co-path variant leaf -> firmware_root) into the
    # manifest region. The device authenticates the manifest against firmware_root
    # using this embedded proof (empty for a single-variant firmware).
    manifest = firmware_module.read_manifest(fw)
    proof = firmware_module.read_manifest_proof(fw)
    module_headers = firmware_module.read_manifest_region(fw)
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
        f"proof: {len(proof)} node(s) | modules: {names} | "
        f"phase-1: {mode}"
    )

    # --- TEST fault injection (--tamper). Phase-1 faults mutate the boot header /
    #     manifest here; phase-2 faults are applied inside _run(). ---
    tamper = args.tamper
    if tamper == "wrong-model":
        b = bytearray(boot_header)
        b[4] ^= 0xFF  # hw_model is the u32 at offset 4 of the boot header
        boot_header = bytes(b)
        print("TEST[wrong-model]: flipped hw_model in the boot header")
    elif tamper == "bl-sig":
        b = bytearray(boot_header)
        b[len(b) // 2] ^= 0xFF  # a byte in the (large) SLH signature region
        boot_header = bytes(b)
        print(
            "TEST[bl-sig]: flipped a boot-header signature byte -- forces the "
            "full-bootloader path; staging verifies the sig and rejects"
        )
    elif tamper == "fw-sig":
        m = bytearray(module_headers)
        m[64] ^= 0xFF  # a manifest byte -> variant leaf no longer folds to root
        module_headers = bytes(m)
        print("TEST[fw-sig]: flipped a manifest byte (fold != firmware_root)")
    elif tamper == "custom-app-size":
        # CUSTOM only: the app entry's size is zeroed-for-fold (NOT founder-
        # authenticated), so inflating it still FOLDS -- but the layout check
        # (fwt_manifest_layout_valid, now run in phase 1) must reject a module that
        # runs past the firmware area. Mutate the phase-1 manifest so the device
        # rejects during FirmwareBegin, BEFORE the user is asked to confirm and
        # before it stages the boot header + reboots. Kept chunk-aligned so the
        # bounds check fires (not the alignment check).
        if not firmware_module.is_custom_firmware(fw):
            raise SystemExit(
                "custom-app-size needs the CUSTOM variant (only there is the app "
                "size unauthenticated): "
                'make upload_pq VARIANT=custom UPLOAD_OPTS="--tamper custom-app-size"'
            )
        hdr_len = firmware_module._MANIFEST_FIXED.size
        ent_len = firmware_module._MANIFEST_ENTRY.size
        app_i = next(
            i
            for i, e in enumerate(firmware_module.manifest_entries(fw))
            if e["module_type"] == firmware_module.FW_MODULE_APP
        )
        off = hdr_len + app_i * ent_len + 16  # size: after type+flags+addr+chunk_size
        m = bytearray(module_headers)
        orig = int.from_bytes(m[off : off + 4], "little")
        bloated = orig + 0x0040_0000  # +4 MiB, chunk-aligned, past the fw area
        m[off : off + 4] = bloated.to_bytes(4, "little")
        module_headers = bytes(m)
        print(
            f"TEST[custom-app-size]: inflated custom app size {orig} -> {bloated} in"
            " the phase-1 manifest (still folds -- size zeroed for custom; device"
            " must reject at FirmwareBegin, before confirm)"
        )

    def _run() -> None:
        # --- Phase 1 ---
        print(f"phase 1: FirmwareBegin ({mode}) ...")
        _client, session = connect()
        if session.features.bootloader_mode is not True:
            raise SystemExit("device must be in bootloader mode")
        streamed = firmware.firmware_begin(
            session, boot_header, module_headers, code=bl_code
        )
        # Both cases stage the new boot header and reboot; the boardloader applies
        # it via the UCB, then the freshly-booted bootloader installs the firmware
        # modules (phase 2). Only the full path also replaces the bootloader code.
        if streamed:
            done = (
                "full bootloader streamed -- device's choice); device is rebooting "
                "to install the new bootloader, then the firmware (phase 2)"
            )
        else:
            done = (
                "header-only -- device's choice, bootloader code unchanged); device "
                "is rebooting to apply the new boot header, then install the firmware "
                "(phase 2)"
            )
        print(f"phase 1 done ({done} ...")

        # --- Reconnect across the boardloader-mediated reboot ---
        time.sleep(3)
        session2 = connect(retries=args.reconnect_retries)[1]
        print("reconnected in bootloader mode; phase 2: streaming firmware ...")

        # --- Phase 2: inline per-chunk prev_hashes from the GENUINE image;
        #     phase-2 --tamper cases mutate the uploaded payload / the inline
        #     hash map here. prev_hashes maps a chunk's image offset -> its chain
        #     H_prev (see build_chunk_prev_hashes); it is sent inline on each
        #     FirmwareUpload. ---
        prev_hashes = firmware_module.build_chunk_prev_hashes(fw)
        upload_fw = fw
        if tamper == "corrupt-chunk":
            buf = bytearray(fw)
            buf[args.tamper_offset] ^= 0xFF
            upload_fw = bytes(buf)
            print(
                f"TEST[corrupt-chunk]: flipped upload byte 0x{args.tamper_offset:x}"
                " (hashes + manifest genuine)"
            )
        elif tamper == "chunk-hash":
            if not prev_hashes:
                raise SystemExit(
                    "chunk-hash needs a multi-chunk module (no inline hashes)"
                )
            # The device only looks up the TRAILING chunk of each transport block,
            # and the block size is device-chosen, so flip EVERY inline hash to
            # guarantee the first block's trailing intermediate is wrong -> the
            # block reconstruction mismatches -> "Invalid chunk hash".
            for off in list(prev_hashes):
                b = bytearray(prev_hashes[off])
                b[0] ^= 0xFF
                prev_hashes[off] = bytes(b)
            print(
                f"TEST[chunk-hash]: flipped all {len(prev_hashes)} inline prev_hashes"
            )
        elif tamper == "missing-chunk-hash":
            if not prev_hashes:
                raise SystemExit(
                    "missing-chunk-hash needs a multi-chunk module (no inline hashes)"
                )
            # Drop ALL inline hashes; the first non-last block then arrives with no
            # trailing intermediate -> device rejects "missing chunk hash". (Block
            # size is device-chosen, so we can't target one guaranteed-used entry.)
            dropped = len(prev_hashes)
            prev_hashes = {}
            print(f"TEST[missing-chunk-hash]: dropped all {dropped} inline prev_hashes")
        elif tamper == "variant-swap":
            other = _find_other_variant(args.firmware)
            other_fw = other.read_bytes()
            upload_fw = other_fw
            prev_hashes = firmware_module.build_chunk_prev_hashes(other_fw)
            print(
                f"TEST[variant-swap]: phase 1 approved {args.firmware.name}, "
                f"streaming {other.name}"
            )
        firmware.update(session2, upload_fw, prev_hashes=prev_hashes)
        print("phase 2 done; firmware installed.")

    # --- Run, with an optional expect-a-rejection assertion (--tamper self-asserts). ---
    expect = args.expect_failure or (_TAMPERS.get(tamper) if tamper else None)
    if expect is None:
        _run()
        return
    try:
        _run()
    except exceptions.TrezorFailure as e:
        got = str(e)
        if expect in got:
            print(f"PASS: device rejected as expected ({got})")
            return
        raise SystemExit(f"FAIL: expected a Failure containing '{expect}', got: {got}")
    raise SystemExit(f"FAIL: expected rejection ('{expect}') but the update succeeded")


if __name__ == "__main__":
    main()
