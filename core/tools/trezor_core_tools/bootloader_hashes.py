#!/usr/bin/env python3

from hashlib import blake2s
from pathlib import Path

import click

from trezorlib.firmware.core import FirmwareImage, Model

from .common import MODELS_DIR
from .layout_parser import find_value

TEMPLATE = """\
#ifndef BOOTLOADER_HASHES_H
#define BOOTLOADER_HASHES_H

// Auto-generated file, do not edit.

// clang-format off
{patterns}
// clang-format on

#endif
"""

PATTERN = """\
// {name} version {version}
#define BOOTLOADER_{suffix}_00 {{{bytes_00}}}
#define BOOTLOADER_{suffix}_FF {{{bytes_ff}}}
"""


def aligned_digest(fn: Path, data: bytes, padding: bytes, aligned_size: int) -> bytes:
    """Calculate digest of data, aligned to aligned_size with
    the specified padding.

    Firmware needs to check the bootloader against a digest padded either by 0xff
    (unwritten NOR-flash byte) or 0x00 (explicitly cleared byte).
    """
    if len(data) > aligned_size:
        raise ValueError(fn, "too big")

    assert len(padding) == 1
    digest_data = data + padding * (aligned_size - len(data))
    assert len(digest_data) == aligned_size
    return blake2s(digest_data).digest()


def to_uint_array(data: bytes) -> str:
    """Convert bytes to C array of uint8_t, like so:

    >>> to_uint_array(b"\\x00\\x01\\x02")
    "{0x00, 0x01, 0x02}"
    """
    return ", ".join([f"0x{i:02x}" for i in data])


def bootloader_str(file: Path, model: str) -> str:
    """From a given file, generate the relevant C definition strings from PATTERN.

    Calculates the two padded hashes, one with 0x00 and the other 0xFF, and returns
    a string suitable for writing into bl_check.c.
    """
    data = file.read_bytes()

    suffix = file.stem[len("bootloader_") :].upper()

    aligned_size = find_value(model, "BOOTLOADER_MAXSIZE", False)

    bytes_00 = to_uint_array(aligned_digest(file, data, b"\x00", aligned_size))
    bytes_ff = to_uint_array(aligned_digest(file, data, b"\xff", aligned_size))

    bl = FirmwareImage.parse(data)
    version_str = ".".join(str(x) for x in bl.header.version)
    if not isinstance(bl.header.hw_model, Model):
        raise ValueError(
            f"Model mismatch: {file.name} {model} (found {bytes(bl.header.hw_model).decode()})"
        )
    elif bl.header.hw_model.value != model.encode():
        raise ValueError(
            f"Model mismatch: {file.name} {model} (found {bl.header.hw_model.value})"
        )

    return PATTERN.format(
        name=file.name,
        version=version_str,
        suffix=suffix,
        bytes_00=bytes_00,
        bytes_ff=bytes_ff,
    )


@click.command()
@click.option("-c", "--check", is_flag=True, help="Do not write, only check.")
def main(check):

    models = list(MODELS_DIR.iterdir())

    models = [model for model in models if model.is_dir()]

    for model in models:

        path = model / "bootloaders"

        if path.is_dir():

            header_file = path / "bootloader_hashes.h"

            patterns = []

            bootloaders = sorted(path.glob("bootloader*.bin"))
            for bootloader in bootloaders:
                print(f"Processing {bootloader}")
                patterns.append(bootloader_str(bootloader, model.name))

            content = TEMPLATE.format(patterns="\n".join(patterns))

            if not check:
                header_file.write_text(content)
            else:
                actual = header_file.read_text()
                if content != actual:
                    raise click.ClickException(f"{header_file} differs from expected")


if __name__ == "__main__":
    main()
