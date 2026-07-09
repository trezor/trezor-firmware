#!/usr/bin/env python3
"""Verify that a SIGNED firmware/secmon/bootloader binary matches the UNSIGNED one.

Two things are checked for every pair:

\b
  1. Equivalence -- the signed binary is identical to the one you sent EXCEPT in
     the signature-carrying fields. We parse both images, zero those fields,
     rebuild, and compare. This covers the vendor header, the firmware/boot
     header, and the entire code body -- everything signing is NOT allowed to
     touch.

\b
  2. Authenticity -- the signature on the signed file is cryptographically valid
     against the PRODUCTION keys (mandatory, not optional). This also
     re-validates the code hashes / Merkle root.

\b
Supported image types (auto-detected from the 4-byte magic):
    TRZV  firmware (vendor header + firmware header + code)   -> all current models
    TSEC  secmon
    TRZB  legacy bootloader (CoSi-signed firmware image)
    TRZQ  PQ bootloader (SLH-DSA + ed25519 signatures)        -> Safe 7

\b
On secmon models the prodtest is a secmon-signed body wrapped in a vendor +
firmware header, carrying TWO signatures (the embedded secmon header and the
outer firmware header). Such images are detected automatically; on top of the
usual checks, the wrapper itself is pinned down: the code section must be
EXACTLY the embedded secmon image (nothing else), the vendor header must be
byte-identical to the committed prodtest vendor header for the model, and the
embedded secmon signature is verified against the production secmon keys.

\b
Usage:
    verify_signed_firmware.py UNSIGNED.bin SIGNED.bin   # explicit pair
    verify_signed_firmware.py SIGNED.bin                # derive UNSIGNED by dropping "-signed"
    verify_signed_firmware.py                           # scan ./ for *-signed.bin pairs

Exit code: 0 only if EVERY pair both matches and is genuinely signed; 1 otherwise.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import click

from trezorlib._internal import firmware_headers as fh
from trezorlib.firmware import FirmwareHeader, SecmonHeader
from trezorlib.firmware.core import FirmwareImage
from trezorlib.firmware.models import Model


# ---- pretty output -------------------------------------------------------
def ok(msg: str) -> None:
    click.echo("  " + click.style("✔", fg="green") + " " + msg)


def bad(msg: str) -> None:
    click.echo("  " + click.style("✘", fg="red") + " " + msg)


def info(msg: str) -> None:
    click.echo("  " + click.style("•", fg="yellow") + " " + msg)


# ---- trezorlib glue ------------------------------------------------------
def parse_any(data: bytes) -> fh.SignableImageProto | fh.BootloaderV2Image:
    """Parse any supported image. parse_image() doesn't dispatch TRZQ, so do it here."""
    if data[:4] == b"TRZQ":
        return fh.BootloaderV2Image.parse(data)
    return fh.parse_image(data)


def _inner_secmon(img: fh.VendorFirmware) -> fh.SecmonImage | None:
    """Parse the code section as an embedded secmon image, if it is one.

    On secmon models the prodtest is a secmon-signed body wrapped in a vendor +
    firmware header; the second signature lives in the embedded secmon header.

    A successful parse guarantees the code section is EXACTLY one well-formed
    secmon image: the SecmonImage struct is Terminated, so trailing bytes make
    the parse fail (and the image is then treated as ordinary firmware).
    """
    try:
        return fh.SecmonImage.parse(img.firmware.code)
    except Exception:  # noqa: BLE001
        return None


def _zero_cosi_header(h: FirmwareHeader | SecmonHeader) -> None:
    """Zero the signature fields of a CoSi firmware/secmon/bootloader header."""
    h.signature = b"\x00" * 64
    h.sigmask = 0
    if not isinstance(h, SecmonHeader):
        h.v1_signatures = [b"\x00" * 64] * len(h.v1_signatures)
        h.v1_key_indexes = [0] * len(h.v1_key_indexes)


def normalized(data: bytes) -> bytes:
    """Rebuild the image with all signature-carrying fields zeroed.

    Two images that are identical apart from their signatures produce identical
    normalized bytes. build() round-trips faithfully for unmodified images, so the
    only bytes this changes are the signature fields themselves.
    """
    img = parse_any(data)
    if isinstance(img, fh.VendorFirmware):  # TRZV
        _zero_cosi_header(img.firmware.header)
        inner = _inner_secmon(img)
        if inner is not None:
            # Secmon-wrapped image: the embedded secmon header carries a second
            # signature, and the outer code hashes cover the code including that
            # signature -- zero it and recompute the hashes over the zeroed code.
            _zero_cosi_header(inner.header)
            img.firmware.code = inner.build()
            img.firmware.header.hashes = img.firmware.code_hashes()
    elif isinstance(img, fh.BootloaderV2Image):  # TRZQ
        img.header.sigmask = 0
        img.unauth.slh_signatures = [
            b"\x00" * len(x) for x in img.unauth.slh_signatures
        ]
        img.unauth.ec_signatures = [b"\x00" * len(x) for x in img.unauth.ec_signatures]
    elif isinstance(img, fh.SecmonImage | fh.BootloaderImage | FirmwareImage):
        # TSEC | TRZB | bare FirmwareImage
        _zero_cosi_header(img.header)
    else:
        raise TypeError(f"don't know how to normalize image type {type(img).__name__}")
    return img.build()


def _check_vendor_header(img: fh.VendorFirmware) -> bool:
    """The wrapper's vendor header must be the committed prodtest vendor header.

    The rest of the wrapper needs no dedicated check: the outer firmware header
    is covered by the normalized comparison against the unsigned build, and the
    code section is exactly the embedded secmon image (see _inner_secmon).
    """
    model = Model.from_hw_model(img.vendor_header.hw_model).value.decode()
    vh_rel = f"embed/models/{model}/vendorheader/vendorheader_prodtest_signed_prod.bin"
    vh_file = Path(__file__).resolve().parents[2] / vh_rel
    if not vh_file.is_file():
        bad(
            f"cannot check the wrapper vendor header: {vh_rel} not found "
            "(not running from the firmware repository?)"
        )
        return False
    if img.vendor_header.build() != vh_file.read_bytes():
        bad(f"vendor header does NOT match the committed {vh_rel}")
        return False
    ok(f"vendor header is byte-identical to the committed {vh_rel}")
    return True


def _runs(offsets: list[int]) -> int:
    """Count contiguous runs in a sorted list of byte offsets."""
    runs = 0
    prev = None
    for o in offsets:
        if prev is None or o != prev + 1:
            runs += 1
        prev = o
    return runs


# ---- core verification of one (unsigned, signed) pair --------------------
def verify_pair(unsigned: Path, signed: Path) -> bool:
    click.echo()
    click.echo(click.style(f"== {signed.name}", bold=True))

    for f in (unsigned, signed):
        if not f.is_file():
            bad(f"missing file: {f}")
            return False

    if unsigned.samefile(signed):
        bad("both arguments are the SAME file")
        return False

    u = unsigned.read_bytes()
    s = signed.read_bytes()

    if len(u) != len(s):
        bad(f"size mismatch: unsigned={len(u)} signed={len(s)} -> NOT the same build")
        return False

    try:
        img = parse_any(s)
    except Exception as e:  # noqa: BLE001
        bad(f"could not parse signed image (magic={s[:4]!r}): {type(e).__name__}: {e}")
        return False
    info(
        f"type: {getattr(img, 'NAME', '?')} ({s[:4].decode('ascii', 'replace')})   size: {len(s)} B"
    )

    okall = True

    # ---- CHECK 0: secmon-wrapped images (prodtest on secmon models) --------
    inner = _inner_secmon(img) if isinstance(img, fh.VendorFirmware) else None
    if inner is not None:
        info("secmon-wrapped image detected (prodtest on secmon models)")
        okall &= _check_vendor_header(img)

    # ---- CHECK 1 (decisive): identical except the signature fields ---------
    try:
        nu, ns = normalized(u), normalized(s)
    except Exception as e:  # noqa: BLE001
        bad(f"could not normalize for comparison: {type(e).__name__}: {e}")
        return False

    if nu == ns:
        digest = hashlib.sha256(ns).hexdigest()
        ok(f"identical except signature fields, normalized sha256: {digest}")
    else:
        bad(
            "content differs OUTSIDE the signature fields -- signed binary does NOT match!"
        )
        if len(nu) != len(ns):
            info(f"  normalized sizes differ: {len(nu)} vs {len(ns)}")
        nd = [i for i in range(min(len(nu), len(ns))) if nu[i] != ns[i]]
        if nd:
            info(
                f"  first content difference at byte {nd[0]} ({len(nd)} content bytes differ)"
            )
        okall = False

    # ---- CHECK 2 (diagnostic): what actually changed -----------------------
    diffs = [i for i in range(len(u)) if u[i] != s[i]]
    if not diffs:
        bad(
            "files are byte-for-byte IDENTICAL -- nothing was (re)signed; a genuine "
            "signing changes the signature fields. Wrong files?"
        )
        okall = False
    else:
        confined = " [all within signature fields]" if nu == ns else ""
        info(f"{len(diffs)} bytes differ across {_runs(diffs)} run(s){confined}")

    # ---- CHECK 3: signature authenticity, on every signature layer ---------
    layers = [(getattr(img, "NAME", "image"), img)]
    if inner is not None:
        layers.append(("embedded secmon", inner))
    for what, layer in layers:
        try:
            if not layer.signature_present():
                bad(f"no signature present in the {what}")
                okall = False
            else:
                layer.verify()  # production keys; raises on bad signature or bad hashes
                ok(f"{what} signature is GENUINE -- verified against production keys")
        except Exception as e:  # noqa: BLE001
            bad(
                f"{what} signature verification FAILED against production keys: "
                f"{type(e).__name__}: {e}"
            )
            okall = False

    # ---- the canonical fingerprint(s), for cross-checking against the ------
    # ---- published fingerprints and the values confirmed when signing ------
    try:
        if isinstance(img, fh.BootloaderV2Image):
            info(f"fingerprint (merkle root): {img.merkle_root().hex(' ', 2)}")
        elif inner is not None:
            info(
                f"fingerprint (embedded secmon, as published): {inner.digest().hex(' ', 2)}"
            )
            info(
                f"fingerprint (outer image, as confirmed when signing): {img.digest().hex(' ', 2)}"
            )
        else:
            info(f"fingerprint: {img.digest().hex(' ', 2)}")
    except Exception as e:  # noqa: BLE001
        bad(f"could not compute the fingerprint: {type(e).__name__}: {e}")
        okall = False

    return okall


# ---- argument handling ---------------------------------------------------
def collect_pairs(files: list[Path]) -> list[tuple[Path, Path]]:
    if len(files) == 2:
        return [(files[0], files[1])]

    if len(files) == 1:
        signed = files[0]
        if not signed.name.endswith("-signed.bin"):
            raise click.UsageError("Single-argument form expects a *-signed.bin file.")
        return [(signed.with_name(signed.name.replace("-signed.bin", ".bin")), signed)]

    if len(files) == 0:
        pairs = [
            (signed.with_name(signed.name.replace("-signed.bin", ".bin")), signed)
            for signed in sorted(Path.cwd().glob("*-signed.bin"))
        ]
        if not pairs:
            raise click.UsageError(
                f"No *-signed.bin files in {Path.cwd()}. Pass files explicitly; see --help."
            )
        return pairs

    raise click.UsageError("Too many arguments (expected 0, 1, or 2). See --help.")


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=__doc__,
)
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(path_type=Path),
)
def main(files: tuple[Path, ...]) -> None:
    pairs = collect_pairs(list(files))

    # Evaluate every pair (do not short-circuit) so each gets reported.
    results = [verify_pair(unsigned, signed) for unsigned, signed in pairs]
    all_ok = all(results)

    click.echo()
    if all_ok:
        click.echo(
            click.style(
                "ALL PAIRS VERIFIED -- signed binaries match the unsigned ones "
                "(signature fields only) and are genuinely signed.",
                fg="green",
                bold=True,
            )
        )
        return
    click.echo(click.style("VERIFICATION FAILED -- see above.", fg="red", bold=True))
    sys.exit(1)


if __name__ == "__main__":
    main()
