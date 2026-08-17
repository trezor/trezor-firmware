#!/usr/bin/env python3

from hashlib import blake2s
from pathlib import Path

import click
import construct as c

from trezorlib.firmware.core import BootableImage, FirmwareImage
from trezorlib.firmware.models import Model

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


def model_uses_boot_ucb(model_dir: Path) -> bool:
    """Whether the model enables the UCB (update control block) bootloader scheme.

    UCB models verify a staged bootloader through its PQ boot-header signature
    (see boot_image_replace under USE_BOOT_UCB), not through the padded blake2s
    digests in bootloader_hashes.h -- boot_image_embdata.c only wires
    .hash_00/.hash_FF ``#ifndef USE_BOOT_UCB``. The digests are dead for these
    models, so generating them only churns the header whenever the bootloader
    binary changes, for no consumer.

    The authoritative source is the model.toml ``features`` list; the BOOTUCB_*
    layout symbols are not reliable (some non-UCB models define them too).
    """
    model_toml = model_dir / "model.toml"
    if not model_toml.is_file():
        return False
    for raw in model_toml.read_text().splitlines():
        # tolerate leading indentation, a trailing comma and inline comments
        line = raw.split("#", 1)[0].strip().rstrip(",").strip()
        if line == '"boot_ucb"':
            return True
    return False


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

    try:
        bl = BootableImage.parse(data)
    except c.ConstructError:
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
def main(check: bool) -> None:

    models = list(MODELS_DIR.iterdir())

    models = [model for model in models if model.is_dir()]

    for model in models:

        if model_uses_boot_ucb(model):
            # UCB models never consume these digests (see model_uses_boot_ucb):
            # both the header and its #include have been removed for them, so
            # skip generation to avoid recreating a dead file.
            print(f"Skipping {model.name}: boot_ucb model, bootloader hashes unused")
            continue

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
