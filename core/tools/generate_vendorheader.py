#!/usr/bin/env python3
from __future__ import annotations

import json
import typing as t
from pathlib import Path

import click
from trezor_core_tools.common import CORE, MODELS_DIR

from trezorlib import cosi, firmware, toif
from trezorlib._internal import firmware_headers

ROOT = CORE.parent

# headers that are also stored signed with the development keys
DEV_SIGNED = ("unsafe", "dev_DO_NOT_SIGN", "prodtest_DO_NOT_SIGN")


def display(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def header_path(specfile: Path, kind: str) -> Path:
    name = specfile.stem.removeprefix("vendor_")
    return specfile.parent / f"vendorheader_{name}_{kind}.bin"


def minimum_header_len(spec: dict[str, t.Any]) -> int:
    spec = spec.copy()
    spec["header_len"] = 512000
    reparsed = firmware.VendorHeader.SUBCON.parse(
        firmware.VendorHeader.SUBCON.build(spec)
    )
    # data length + 65 for signatures
    return reparsed._end_offset - reparsed._start_offset + 65


def build_unsigned(specfile: Path, image: Path | None, verbose: bool) -> bytes:
    where = display(specfile)
    if image is None:
        image = specfile.with_suffix(".toif")
    if not image.exists():
        raise click.ClickException(f"{where}: image {display(image)} does not exist.")

    spec = json.loads(specfile.read_text())
    spec["pubkeys"] = [bytes.fromhex(k) for k in spec["pubkeys"]]
    spec["image"] = toif.ToifStruct.parse(image.read_bytes())
    spec["sigmask"] = 0
    spec["signature"] = b"\x00" * 64
    if spec["hw_model"] is None:
        spec["hw_model"] = b"\x00\x00\x00\x00"
    else:
        spec["hw_model"] = spec["hw_model"].encode("ascii")
    spec.setdefault("fw_type", 0)

    min_bytes = minimum_header_len(spec)
    # rounded up to nearest multiple of 512
    spec.setdefault("header_len", (min_bytes + 511) // 512 * 512)
    if spec["header_len"] < min_bytes:
        raise click.ClickException(
            f"{where}: header_len {spec['header_len']} too low, "
            f"the header needs {min_bytes} bytes."
        )
    if spec["header_len"] % 512 != 0:
        raise click.ClickException(f"{where}: header_len must be a multiple of 512.")
    if verbose:
        click.echo(
            f"{where}: header_len {spec['header_len']} (needs {min_bytes} bytes)"
        )

    return firmware.VendorHeader.SUBCON.build(spec)


def sign_with_dev_keys(vh_bytes: bytes) -> bytes:
    vh = firmware_headers.VendorHeader.parse(vh_bytes)
    signature = cosi.sign_with_privkeys(vh.digest(), vh.DEV_KEYS, deterministic=True)
    vh.insert_signature(signature, (1 << len(vh.DEV_KEYS)) - 1)
    return vh.build()


def build_files(specfile: Path, verbose: bool = False) -> dict[Path, bytes]:
    """Build the unsigned header and, if listed in DEV_SIGNED, its dev-signed copy."""
    unsigned = build_unsigned(specfile, None, verbose)
    files = {header_path(specfile, "unsigned"): unsigned}
    if specfile.stem.removeprefix("vendor_") in DEV_SIGNED:
        files[header_path(specfile, "signed_dev")] = sign_with_dev_keys(unsigned)
    return files


FilePath = click.Path(exists=True, dir_okay=False, path_type=Path)


@click.command()
@click.argument("specfiles", nargs=-1, type=FilePath)
@click.option("-i", "--image", type=FilePath, help="Image (default: SPECFILE.toif).")
@click.option(
    "-o",
    "--outfile",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file (default: next to SPECFILE).",
)
@click.option("-c", "--check", is_flag=True, help="Check but do not write headers.")
def main(
    specfiles: tuple[Path, ...], image: Path | None, outfile: Path | None, check: bool
) -> None:
    """Build vendor headers from their JSON specs.

    Without SPECFILES, rebuild the vendor headers of all models, including the
    copies signed with development keys. With --image or --outfile, build only
    the unsigned header of a single SPECFILE.
    """
    files: dict[Path, bytes] = {}
    if image or outfile:
        if len(specfiles) != 1:
            raise click.UsageError("--image and --outfile need exactly one SPECFILE.")
        outfile = outfile or header_path(specfiles[0], "unsigned")
        files[outfile] = build_unsigned(specfiles[0], image, verbose=True)
    elif specfiles:
        for specfile in specfiles:
            files.update(build_files(specfile, verbose=True))
    else:
        count = 0
        for vh_dir in sorted(MODELS_DIR.glob("*/vendorheader")):
            names = []
            for specfile in sorted(vh_dir.glob("*.json")):
                spec_files = build_files(specfile)
                name = specfile.stem.removeprefix("vendor_")
                names.append(name + "*" if len(spec_files) > 1 else name)
                files.update(spec_files)
            click.echo(f"{vh_dir.parent.name}: {', '.join(names)}")
            count += len(names)
        click.echo(f"{count} vendor headers (* = also signed with development keys)")

    outdated = [
        path
        for path, data in files.items()
        if not path.exists() or path.read_bytes() != data
    ]
    for path in outdated:
        if check:
            click.echo(f"{display(path)} is outdated")
        else:
            path.write_bytes(files[path])
            click.echo(f"Updated {display(path)}")
    if check and outdated:
        raise click.ClickException("Vendor headers are not up to date.")


if __name__ == "__main__":
    main()
