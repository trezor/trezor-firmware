#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path
import os
import sys

NRF_HEADER_MAGIC = b"TRZN"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Wrap nRF firmware with header containing image_type and BBHI version."
    )

    parser.add_argument(
        "input_file",
        help="Input nRF firmware file",
    )

    parser.add_argument(
        "-v",
        "--version",
        required=True,
        help="Version tuple as 'major.minor.patch+tweak' (required)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file (defaults to wrapped_<input>.bin)",
    )

    args = parser.parse_args()

    args.version = decode_version(args.version)
    return args


def decode_version(version: str) -> tuple[int, int, int, int]:
    try:
        parts = version.replace(".", ",").replace("+", ",").split(",")
        version_tuple = tuple(int(x.strip()) for x in parts)
    except ValueError:
        sys.exit(
            "Error: version should be in format 'major.minor.patch+tweak' "
            "(separators can be '.', ',' or '+')"
        )

    if len(version_tuple) != 4:
        sys.exit("Error: version must have exactly 4 values")

    return version_tuple


def wrap_firmware(
    version_tuple: tuple[int, int, int, int],
    firmware_path: str,
    output_path: str,
):
    firmware_data = Path(firmware_path).read_bytes()
    SIGMASK = 0x00
    header = struct.pack("<4s B BBHI", NRF_HEADER_MAGIC, SIGMASK, *version_tuple)

    Path(output_path).write_bytes(header + firmware_data)
    print(f"Wrapped firmware written to {output_path}")


def main():
    args = parse_args()

    # Determine output file name
    output_file = args.output or f"wrapped_{os.path.basename(args.input_file)}"

    wrap_firmware(
        version_tuple=args.version,
        firmware_path=args.input_file,
        output_path=output_file,
    )


if __name__ == "__main__":
    main()
