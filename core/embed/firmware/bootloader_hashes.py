#!/usr/bin/env python3
from pathlib import Path
from hashlib import blake2s

from trezorlib.firmware.core import FirmwareImage

ALIGNED_SIZE = 128 * 1024

HERE = Path(__file__).parent
BOOTLOADERS = HERE / ".." / "models"

BL_CHECK = HERE / "bl_check.c"

BL_CHECK_AUTO_BEGIN = "// --- BEGIN GENERATED BOOTLOADER SECTION ---\n"
BL_CHECK_AUTO_END = "// --- END GENERATED BOOTLOADER SECTION ---\n"

PATTERN = """\
// {name} version {version}
#define BOOTLOADER_{suffix}_00 {{{bytes_00}}}
#define BOOTLOADER_{suffix}_FF {{{bytes_ff}}}
"""


def aligned_digest(data: bytes, padding: bytes) -> bytes:
    """Calculate digest of data, aligned to ALIGNED_SIZE with
    the specified padding.

    Firmware needs to check the bootloader against a digest padded either by 0xff
    (unwritten NOR-flash byte) or 0x00 (explicitly cleared byte).
    """
    if len(data) > ALIGNED_SIZE:
        raise ValueError(fn, "too big")

    assert len(padding) == 1
    digest_data = data + padding * (ALIGNED_SIZE - len(data))
    assert len(digest_data) == ALIGNED_SIZE
    return blake2s(digest_data).digest()


def to_uint_array(data: bytes) -> str:
    """Convert bytes to C array of uint8_t, like so:

    >>> to_uint_array(b"\\x00\\x01\\x02")
    "{0x00, 0x01, 0x02}"
    """
    return ", ".join([f"0x{i:02x}" for i in data])


def bootloader_str(file: Path) -> str:
    """From a given file, generate the relevant C definition strings from PATTERN.

    Calculates the two padded hashes, one with 0x00 and the other 0xFF, and returns
    a string suitable for writing into bl_check.c.
    """
    data = file.read_bytes()

    suffix = file.stem[len("bootloader_") :].upper()
    bytes_00 = to_uint_array(aligned_digest(data, b"\x00"))
    bytes_ff = to_uint_array(aligned_digest(data, b"\xff"))

    try:
        bl = FirmwareImage.parse(data)
        version_str = ".".join(str(x) for x in bl.header.version)
    except Exception:
        version_str = "<unknown>"

    return PATTERN.format(
        name=file.name,
        version=version_str,
        suffix=suffix,
        bytes_00=bytes_00,
        bytes_ff=bytes_ff,
    )


def main():

    models = list(BOOTLOADERS.iterdir())

    models = [model for model in models if model.is_dir()]

    for model in models:

        path = model / "bootloaders"

        if path.is_dir():

            header_file = path / "bootloader_hashes.h"

            content = []
            content.append("#ifndef BOOTLOADER_HASHES_H\n")
            content.append("#define BOOTLOADER_HASHES_H\n")
            content.append("\n")
            content.append("// Auto-generated file, do not edit.\n")
            content.append("\n")
            content.append("// clang-format off\n")

            bootloaders = sorted(path.glob("bootloader*.bin"))
            for bootloader in bootloaders:
                if bootloader.is_file():
                    print(f"Processing {bootloader}")
                    content.append(bootloader_str(bootloader))

            content.append("// clang-format on\n")
            content.append("\n")
            content.append("#endif\n")

            header_file.write_text("".join(content))


if __name__ == "__main__":
    main()
