#!/usr/bin/env python3
"""Prototype orchestrator for a Merkle-tree (pq_secure_boot) OTA update.

Phase 1: FirmwareBegin (boot header + manifest region), confirm, reboot.
Phase 2: FirmwareErase + stream firmware.bin, verified against firmware_root.
PROTOTYPE: reconnect across the reboot is best-effort; needs a device/emulator.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from trezorlib import device, exceptions, firmware, messages
from trezorlib.client import Session, TrezorClient, get_default_client
from trezorlib.firmware import pq_secure

# TEST-ONLY fault injections -> expected device Failure substring.
_TAMPERS = {
    "fw-sig": "Firmware manifest not authentic",  # ph1: manifest byte flipped
    "wrong-model": "Invalid boot header",  # ph1: hw_model patched
    "variant-swap": "Firmware variant mismatch",  # ph2: sibling variant streamed
    "corrupt-chunk": "Invalid chunk hash",  # ph2: payload byte flipped (after retries)
    "chunk-hash": "Invalid chunk hash",  # ph2: inline prev_hash flipped
    "missing-chunk-hash": "missing chunk hash",  # ph2: inline prev_hash dropped
    # ph1, CUSTOM only: app size is not authenticated, layout check must reject.
    "custom-app-size": "Invalid firmware manifest",
    "custom-app-unaligned": "Invalid firmware manifest",
    # ph1: forces the full-bootloader path; preamble rejects before confirm.
    "bl-sig": "Invalid boot header signature",
    # ph1: co-processor slot no longer folds to modelRoot (STM half of TRZP binding).
    "nrf-copath": "nRF image not in founder tree",
    # ph1: no nRF fields at all; requirement comes from the device build (USE_SMP).
    "no-nrf": "Release carries no co-processor image",
    # Interaction-less consent (FIRMWARE mode): only the consent digest catches these.
    "consent-mismatch": "Firmware mismatch",  # ph1 delivers a sibling variant
    "bad-preamble": "Invalid firmware header",  # firmware-side: unparsable preamble
    "vendor-change": "Different firmware vendor",  # firmware-side: sibling variant
    # ph2 with no ph1 (BOOTLOADER mode): CONTINUE_UPGRADE not armed.
    "bare-phase-2": "must begin with FirmwareBegin",
}


def _other_variant(args: argparse.Namespace) -> pq_secure.PqSecureBundle:
    """A different, genuine variant of the same release (folds to the same root)."""
    if args.bundle is not None:
        names = pq_secure.PqSecureBundle.variants(args.bundle)
        other = next((n for n in names if n != args.variant), None)
        if other is None:
            raise SystemExit(
                "this tamper case needs a bundle with at least two variants; "
                f"{args.bundle} has {names or 'none'}"
            )
        return pq_secure.PqSecureBundle.load(args.bundle, other)

    # Loose files: the filename is all there is to go on.
    for candidate in sorted(args.firmware.parent.glob("*.bin")):
        if candidate.name not in (args.firmware.name, args.bootloader.name):
            return pq_secure.PqSecureBundle(
                args.bootloader.read_bytes(),
                pq_secure.PqSecureFirmware.parse(candidate.read_bytes()),
                variant_name=candidate.stem,
            )
    raise SystemExit("this tamper case needs a second variant next to --firmware")


def _button_callback(br: "messages.ButtonRequest") -> None:
    print("  -> confirm the action on the device")


def _code_entry_callback() -> str:
    """THP pairing code prompt (FIRMWARE-mode connect only)."""
    while True:
        raw = input("  -> enter the pairing code shown on the device: ")
        code = "".join(c for c in raw if c.isdigit())
        if len(code) == 6:
            return code
        print("     the code is 6 digits")


def connect(retries: int = 1, delay: float = 1.0) -> tuple[TrezorClient, Session]:
    """Open a session to a connected device, retrying while it (re)enumerates."""
    last: Exception | None = None
    for _ in range(retries):
        try:
            client = get_default_client(
                "firmware_pq_update",
                button_callback=_button_callback,
                code_entry_callback=_code_entry_callback,
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
        help="an `xtask release` bundle -- either the output DIR or the "
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
    ap.add_argument(
        "--force-nrf",
        action="store_true",
        help="TEST: omit the nRF image-hash hint so the device can't skip the "
        "update-required check and always streams+pushes the nRF (the image is "
        "still fold-verified). Use to exercise the push when the nRF is already "
        "current.",
    )
    # Must outlast boardloader install + autonomous nRF push (~30 s) + enumeration.
    ap.add_argument("--reconnect-retries", type=int, default=120)
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

    if args.bundle is not None:
        if not args.variant:
            raise SystemExit("--bundle requires --variant (e.g. --variant universal)")
        bundle = pq_secure.PqSecureBundle.load(args.bundle, args.variant)
    else:
        if args.bootloader is None or args.firmware is None:
            raise SystemExit("need --bootloader + --firmware, or --bundle + --variant")
        bundle = pq_secure.PqSecureBundle(
            args.bootloader.read_bytes(),
            pq_secure.PqSecureFirmware.parse(args.firmware.read_bytes()),
            variant_name=args.variant,
        )

    nrf = bundle.nrf
    nrf_image = nrf.image if nrf else None
    nrf_co_path = nrf.co_path if nrf else None
    # --force-nrf withholds the hint so the device cannot skip on a hash match.
    nrf_image_hash = None if (nrf is None or args.force_nrf) else nrf.image_hash

    # Pre-upload guard: the same check trezorctl runs.
    if not args.skip_check:
        try:
            bundle.verify(dev_keys=True)
        except Exception as e:  # noqa: BLE001
            print(f"PRE-UPLOAD CHECK FAILED: {e}", file=sys.stderr)
            raise SystemExit("refusing to upload (override with --skip-check)")

    fw = bundle.firmware.data
    boot_header = bundle.boot_header
    # The device decides header-only vs full bootloader; always offer the code.
    bl_code = bundle.bootloader_code
    mods = bundle.firmware.manifest.entries
    # Preamble = the image's manifest region [manifest || proof struct].
    manifest = bundle.firmware.manifest_bytes
    proof = bundle.firmware.proof
    module_headers = bundle.firmware.manifest_region
    names = [getattr(m.module_type, "name", str(m.module_type)).lower() for m in mods]
    # Detected only to annotate output; there is no host flag for custom.
    is_custom = bundle.firmware.manifest.is_custom
    mode = f"bl code available ({len(bl_code)} B); device decides header-only vs full"
    if is_custom:
        mode += " [CUSTOM/unofficial]"
    if nrf is not None:
        mode += (
            f" + nRF OTA available ({len(nrf.image)} B, "
            f"{len(nrf.co_path) // 32}-node co-path; device decides update-required)"
        )
    print(
        f"boot header: {len(boot_header)} B | manifest: {len(manifest)} B | "
        f"proof: {len(proof)} node(s) | modules: {names} | "
        f"phase-1: {mode}"
    )

    # Phase-1 tampers mutate here; phase-2 tampers are applied inside _run().
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
            "full-bootloader path; the preamble must reject at FirmwareBegin, "
            "before confirm and before any code is streamed"
        )
    elif tamper == "fw-sig":
        m = bytearray(module_headers)
        m[64] ^= 0xFF  # a manifest byte -> variant leaf no longer folds to root
        module_headers = bytes(m)
        print("TEST[fw-sig]: flipped a manifest byte (fold != firmware_root)")
    elif tamper == "nrf-copath":
        if not nrf_co_path:
            raise SystemExit(
                "nrf-copath needs a release with an nRF payload (no co-path here)"
            )
        c = bytearray(nrf_co_path)
        c[0] ^= 0xFF
        nrf_co_path = bytes(c)
        print(
            "TEST[nrf-copath]: flipped a co-path byte -- the slot no longer "
            "folds to the signed modelRoot, so the hint itself fails to verify "
            "and the whole upload is rejected"
        )
    elif tamper == "no-nrf":
        if not nrf_image:
            raise SystemExit(
                "no-nrf needs a release with an nRF payload (nothing to withhold)"
            )
        nrf_image = None
        nrf_co_path = None
        nrf_image_hash = None
        print(
            "TEST[no-nrf]: withholding the nRF fields entirely -- a device that "
            "HAS a co-processor must refuse at FirmwareBegin rather than arm the "
            "UCB and strand itself on new-bootloader + old-co-processor"
        )
    elif tamper == "custom-app-size":
        # Chunk-aligned, so the bounds check fires rather than the alignment check.
        if not bundle.firmware.manifest.is_custom:
            raise SystemExit(
                "custom-app-size needs the CUSTOM variant (only there is the app "
                "size unauthenticated): "
                'make upload_pq_test VARIANT=custom UPLOAD_OPTS="--tamper custom-app-size"'
            )
        hdr_len = pq_secure._MANIFEST_HEADER_SIZE
        ent_len = pq_secure._MANIFEST_ENTRY_SIZE
        app_i = next(
            i
            for i, e in enumerate(bundle.firmware.manifest.entries)
            if e.module_type == pq_secure.ModuleType.APP
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
    elif tamper == "custom-app-unaligned":
        # +1 byte: unaligned on every MCU (FLASH_BLOCK_SIZE 16 on U5, 4 on F4),
        # and still inside the firmware area so only the alignment check fires.
        if not bundle.firmware.manifest.is_custom:
            raise SystemExit(
                "custom-app-unaligned needs the CUSTOM variant (only there is the "
                "app size unauthenticated): make upload_pq_test VARIANT=custom "
                'UPLOAD_OPTS="--tamper custom-app-unaligned"'
            )
        hdr_len = pq_secure._MANIFEST_HEADER_SIZE
        ent_len = pq_secure._MANIFEST_ENTRY_SIZE
        app_i = next(
            i
            for i, e in enumerate(bundle.firmware.manifest.entries)
            if e.module_type == pq_secure.ModuleType.APP
        )
        off = hdr_len + app_i * ent_len + 16  # size: after type+flags+addr+chunk_size
        m = bytearray(module_headers)
        orig = int.from_bytes(m[off : off + 4], "little")
        m[off : off + 4] = (orig + 1).to_bytes(4, "little")
        module_headers = bytes(m)
        print(
            f"TEST[custom-app-unaligned]: custom app size {orig} -> {orig + 1} in the"
            " phase-1 manifest -- still folds and still fits the firmware area, so"
            " only the block-alignment check can reject it (at FirmwareBegin, before"
            " confirm)"
        )

    # Consent cases mutate what phase 1 delivers, leaving the preamble genuine.
    ph1_headers = module_headers

    def _run() -> None:
        nonlocal ph1_headers
        _client, session = connect()

        # ph2 without ph1: bypasses the handoff and phase 1 entirely.
        if tamper == "bare-phase-2":
            if session.features.bootloader_mode is not True:
                raise SystemExit(
                    "bare-phase-2 needs the device ALREADY in bootloader mode "
                    "(and with no update armed -- power-cycle into it by hand)"
                )
            print(
                "TEST[bare-phase-2]: skipping FirmwareBegin; sending FirmwareErase "
                "straight into phase 2"
            )
            firmware.update(session, fw, prev_hashes=bundle.chunk_prev_hashes())
            raise SystemExit("FAIL: bare phase 2 was accepted")

        if (
            tamper in ("consent-mismatch", "bad-preamble", "vendor-change")
            and session.features.bootloader_mode is True
        ):
            raise SystemExit(
                f"{tamper} needs the device in FIRMWARE mode (it exercises the "
                "interaction-less consent path, which only runs on the handoff)"
            )

        # Interaction-less handoff: firmware confirms, hashes the preamble into
        # the consent digest carried by the boot command; phase 1 recomputes it.
        if session.features.bootloader_mode is not True:
            preamble = bundle.consent_preamble()
            # Describe what is actually sent; tamper cases rewrite `preamble`.
            breakdown = (
                f"{len(bundle.boot_header_prefix())} B boot header prefix + "
                f"{len(module_headers)} B manifest region"
            )
            if tamper == "bad-preamble":
                preamble = preamble[: len(preamble) // 3]
                breakdown = "TRUNCATED mid-header"
                print(
                    f"TEST[bad-preamble]: truncated the preamble to {len(preamble)} B"
                    " -- check_firmware_header must refuse to parse it"
                )
            elif tamper == "vendor-change":
                other = _other_variant(args)
                other_region = other.firmware.manifest_region
                preamble = bundle.boot_header_prefix() + other_region
                breakdown = (
                    f"{len(bundle.boot_header_prefix())} B boot header prefix + "
                    f"{len(other_region)} B manifest region FROM "
                    f"{other.variant_name}"
                )
                print(
                    "TEST[vendor-change]: asking firmware to confirm "
                    f"{other.variant_name}"
                    " instead -- its variant maps to a different vendor string"
                )
            print(
                "device is in firmware mode; asking it to confirm the upgrade "
                f"({len(preamble)} B preamble = {breakdown}) ..."
            )
            device.reboot_to_bootloader(
                session,
                boot_command=messages.BootCommand.INSTALL_UPGRADE,
                firmware_preamble=preamble,
            )
            time.sleep(3)
            _client, session = connect(retries=args.reconnect_retries)
            if session.features.bootloader_mode is not True:
                raise SystemExit("device did not enter bootloader mode")
            print("reconnected in bootloader mode; consent carried in the boot command")

            if tamper == "consent-mismatch":
                other = _other_variant(args)
                ph1_headers = other.firmware.manifest_region
                print(
                    f"TEST[consent-mismatch]: confirmed {bundle.variant_name}, "
                    f"delivering {other.variant_name}'s manifest to FirmwareBegin "
                    "(still folds -- only the consent digest differs)"
                )

        # --- Phase 1 ---
        print(f"phase 1: FirmwareBegin ({mode}) ...")
        served = firmware.firmware_begin(
            session,
            boot_header,
            ph1_headers,
            code=bl_code,
            nrf_image=nrf_image,
            nrf_co_path=nrf_co_path,
            nrf_image_hash=nrf_image_hash,
        )
        # `served` = bytes the device actually pulled per image. The nRF is only
        # staged here; the STM->nRF push runs on the phase-2 boot.
        bl_done = (
            f"full bootloader streamed ({served['code']} B)"
            if served["code"]
            else "header-only (bootloader code unchanged)"
        )
        if nrf_image is None:
            nrf_done = "no nRF in bundle"
        elif served["nrf"]:
            nrf_done = (
                f"nRF STAGED ({served['nrf']} B streamed; pushed on the phase-2 boot)"
            )
        else:
            nrf_done = "nRF not staged (device reports it already current)"
        print(f"phase 1 done: {bl_done}; {nrf_done}; rebooting -> phase 2 ...")

        # Reconnect across the reboot; a staged nRF push (~30 s) may come first.
        time.sleep(3)
        session2 = connect(retries=args.reconnect_retries)[1]
        print("reconnected in bootloader mode; phase 2: streaming firmware ...")

        # --- Phase 2: inline prev_hashes from the genuine image (see
        #     build_chunk_prev_hashes); phase-2 tampers mutate here. ---
        prev_hashes = bundle.chunk_prev_hashes()
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
            # Block size is device-chosen, so flip every inline hash.
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
            # Same reason: drop them all.
            dropped = len(prev_hashes)
            prev_hashes = {}
            print(f"TEST[missing-chunk-hash]: dropped all {dropped} inline prev_hashes")
        elif tamper == "variant-swap":
            other = _other_variant(args)
            upload_fw = other.firmware.data
            prev_hashes = other.chunk_prev_hashes()
            print(
                f"TEST[variant-swap]: phase 1 approved {bundle.variant_name}, "
                f"streaming {other.variant_name}"
            )
        firmware.update(session2, upload_fw, prev_hashes=prev_hashes)
        print("phase 2 done; firmware installed.")

    # --tamper self-asserts the expected rejection.
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
