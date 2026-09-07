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
import sys
import time
from pathlib import Path

from trezorlib import device, exceptions, firmware, messages
from trezorlib.client import Session, TrezorClient, get_default_client
from trezorlib.firmware import pq_secure

# TEST-ONLY fault injections -> expected device Failure substring. Phase-1 faults
# reject during FirmwareBegin; phase-2 faults reject during the streaming loop.
# `bl-sig` has no host Failure -- observe the device (boardloader RSOD on reboot).
_TAMPERS = {
    "fw-sig": "Firmware manifest not authentic",  # ph1: manifest byte -> fold != firmware_root
    # ph1: patch hw_model -> boot_header_auth_get rejects it ("Invalid boot header")
    # BEFORE the workflow's own (now-dead) "Wrong model" check.
    "wrong-model": "Invalid boot header",
    # ph2: stream a SIBLING variant of the same release. It FOLDS (firmware_root
    # is the root over every variant), so the fold cannot catch it -- what does
    # is the variant binding against the installed boot header's firmware_type.
    "variant-swap": "Firmware variant mismatch",
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
    # --- interaction-less consent (needs FIRMWARE mode; these exercise the gates
    #     that make an unattended install safe, none of which the cases above
    #     reach: every ph1 tamper above mutates the bytes BEFORE the preamble is
    #     computed, so its consent digest always matches what is delivered) ---
    #
    # ph1: confirm one variant in firmware, then deliver a SIBLING variant. Both
    # fold to firmware_root (it is the root over every variant of a release), so
    # authenticity passes and the consent digest is the ONLY thing left to catch
    # the substitution.
    "consent-mismatch": "Firmware mismatch",
    # firmware-side (Python) gate: hand firmware a preamble that does not parse.
    "bad-preamble": "Invalid firmware header",
    # firmware-side gate: ask firmware to confirm a SIBLING variant. Its vendor
    # string differs (firmware_vendor_str derives it from the variant), and
    # crossing that erases the seed, so firmware refuses before any reboot rather
    # than letting the bootloader fall back to prompting.
    "vendor-change": "Different firmware vendor",
    # ph2 with NO ph1: nothing armed CONTINUE_UPGRADE, so a bare FirmwareErase
    # must not be able to erase a valid firmware. Needs BOOTLOADER mode.
    "bare-phase-2": "must begin with FirmwareBegin",
}


def _other_variant(args: argparse.Namespace) -> pq_secure.PqSecureBundle:
    """A DIFFERENT variant of the same release, loaded whole.

    The tamper cases needing two variants need both to be GENUINE: each folds to
    the same firmware_root and only the identity differs, which is what isolates
    the consent digest and the variant binding from every other check. Loading
    through the bundle rather than globbing for a sibling .bin also means a zip
    works without being extracted first.
    """
    if args.bundle is not None:
        names = pq_secure.PqSecureBundle.variants(args.bundle)
        other = next((n for n in names if n != args.variant), None)
        if other is None:
            raise SystemExit(
                "this tamper case needs a bundle with at least two variants; "
                f"{args.bundle} has {names or 'none'}"
            )
        return pq_secure.PqSecureBundle.load(args.bundle, other)

    for candidate in sorted(args.firmware.parent.glob("*.bin")):
        if candidate.name not in (args.firmware.name, "bootloader.bin"):
            return pq_secure.PqSecureBundle(
                args.bootloader.read_bytes(),
                pq_secure.PqSecureFirmware.parse(candidate.read_bytes()),
                variant_name=candidate.stem,
            )
    raise SystemExit("this tamper case needs a second variant next to --firmware")


# header_size is a uint32 at offset 28 of boot_header_auth_t (sec/boot_header.h:
# magic, hw_model, hw_revision, version[4], fix_version[4], min_prev_version[4],
# monotonic(1), sigmask(1), reserved[2], header_size).
def _button_callback(br: "messages.ButtonRequest") -> None:
    print("  -> confirm the action on the device")


def _code_entry_callback() -> str:
    """THP pairing code prompt.

    Needed only for the FIRMWARE-mode connect: running firmware requires a paired
    channel, whereas the bootloader does not -- so this is asked once, before the
    interaction-less handoff, and not again on the reconnects afterwards.
    """
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
        "--skip-nrf",
        action="store_true",
        help="do not OTA the nRF image even if the bundle carries one",
    )
    ap.add_argument(
        "--force-nrf",
        action="store_true",
        help="TEST: omit the nRF image-hash hint so the device can't skip the "
        "update-required check and always streams+pushes the nRF (the image is "
        "still fold-verified). Use to exercise the push when the nRF is already "
        "current.",
    )
    # The phase-2 boot can run an autonomous nRF push (~30 s, nRF in DFU) BEFORE
    # the device re-advertises/enumerates, so the reconnect window must comfortably
    # exceed boardloader-install + push + enumeration. ~1 attempt/sec.
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

    # Resolve the release. PqSecureBundle.load takes the bundle directory or its
    # zip and, unlike this script's old copy, needs no temp dir kept alive for
    # the run; --bootloader/--firmware stay for driving loose files.
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

    nrf = None if args.skip_nrf else bundle.nrf
    nrf_image = nrf.image if nrf else None
    nrf_co_path = nrf.co_path if nrf else None
    # --force-nrf: withhold the update-required hint so the device cannot skip
    # on a hash match and always streams + pushes (the image is still
    # fold-verified on-device).
    nrf_image_hash = None if (nrf is None or args.force_nrf) else nrf.image_hash

    # --- Pre-upload guard: the boot header must be signed and this variant must
    #     fold to the firmware_root it commits to. bundle.verify() is the same
    #     check trezorctl runs, so the harness cannot drift from the real path.
    #     Dev keys are the norm here. ---
    if not args.skip_check:
        try:
            bundle.verify(dev_keys=True)
        except Exception as e:  # noqa: BLE001
            print(f"PRE-UPLOAD CHECK FAILED: {e}", file=sys.stderr)
            raise SystemExit("refusing to upload (override with --skip-check)")

    fw = bundle.firmware.data
    boot_header = bundle.boot_header
    # Always make the bootloader code (everything after the boot header) available.
    # The DEVICE decides whether to stream it: if its current code already conforms
    # to the new header it does a header-only update and never requests the code;
    # otherwise it requests + streams the full code. No host-side --full-bootloader
    # guess -- the device is the judge.
    bl_code = bundle.bootloader_code
    mods = bundle.firmware.manifest.entries
    # Preamble blob = the firmware image's manifest region [manifest || proof
    # struct] -- the exact bytes at the image start, since the signer bakes the
    # per-variant Merkle proof (co-path variant leaf -> firmware_root) into the
    # manifest region. The device authenticates the manifest against firmware_root
    # using this embedded proof (empty for a single-variant firmware).
    manifest = bundle.firmware.manifest_bytes
    proof = bundle.firmware.proof
    module_headers = bundle.firmware.manifest_region
    names = [getattr(m.module_type, "name", str(m.module_type)).lower() for m in mods]
    # Custom (unofficial) is the authenticated FW_VARIANT_CUSTOM variant; the
    # device derives + gates it (unlocked bootloader, unprivileged). Detected here
    # only to annotate the output -- there is no host flag to send.
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
        if not bundle.firmware.manifest.is_custom:
            raise SystemExit(
                "custom-app-size needs the CUSTOM variant (only there is the app "
                "size unauthenticated): "
                'make upload_pq VARIANT=custom UPLOAD_OPTS="--tamper custom-app-size"'
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

    # Consent cases mutate what phase 1 DELIVERS while leaving the preamble (what
    # the user confirmed) genuine, so the digest comparison is what fails. Every
    # other ph1 tamper mutates before the preamble is built, which keeps the two
    # in agreement and never reaches the consent gate.
    ph1_headers = module_headers

    def _run() -> None:
        nonlocal ph1_headers
        _client, session = connect()

        # --- ph2 without ph1: no CONTINUE_UPGRADE is armed, so FirmwareErase alone
        #     must be refused. Bypasses the handoff and phase 1 entirely. ---
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

        # --- Interaction-less handoff (only when starting from firmware mode) ---
        #     The user confirms the release in the FIRMWARE UI; firmware hashes the
        #     preamble into the consent digest and hands it to the bootloader in the
        #     boot command. Phase 1 below then recomputes that digest over what we
        #     actually deliver and skips its own confirm screen iff they match. A
        #     device already in bootloader mode skips this and confirms on-device.
        if session.features.bootloader_mode is not True:
            preamble = bundle.consent_preamble()
            # Describe what is ACTUALLY sent, not what a genuine run would send:
            # the tamper cases below rewrite `preamble`, and a breakdown recomputed
            # from the untampered inputs would contradict its own total.
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
        # `served` = bytes the device actually pulled per image. Report exactly
        # what happened so an nRF that was skipped (already current) is visible
        # rather than silent. Both cases stage the new boot header + reboot; the
        # boardloader installs it, then the freshly-booted bootloader installs the
        # firmware modules (phase 2). The nRF is only STAGED here (host->STM); the
        # STM->nRF push runs autonomously on the phase-2 boot, before firmware.
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

        # --- Reconnect across the boardloader-mediated reboot ---
        # On the phase-2 boot the new bootloader may FIRST push the staged nRF
        # (deferred from phase 1) over serial recovery -- ~30 s during which the
        # nRF is in DFU and the device does not advertise/enumerate. The retry
        # window (--reconnect-retries) is sized to wait that out; a slow reconnect
        # here is expected on a coupled boot+nRF update, not a failure.
        time.sleep(3)
        session2 = connect(retries=args.reconnect_retries)[1]
        print("reconnected in bootloader mode; phase 2: streaming firmware ...")

        # --- Phase 2: inline per-chunk prev_hashes from the GENUINE image;
        #     phase-2 --tamper cases mutate the uploaded payload / the inline
        #     hash map here. prev_hashes maps a chunk's image offset -> its chain
        #     H_prev (see build_chunk_prev_hashes); it is sent inline on each
        #     FirmwareUpload. ---
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
            other = _other_variant(args)
            upload_fw = other.firmware.data
            prev_hashes = other.chunk_prev_hashes()
            print(
                f"TEST[variant-swap]: phase 1 approved {bundle.variant_name}, "
                f"streaming {other.variant_name}"
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
