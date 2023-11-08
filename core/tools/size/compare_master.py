#!/usr/bin/env python3
"""
Compares the current firmware build with a master one
and prints the differences.

Fails if the current changes are increasing the size by a lot.

Also generates a thorough report of the current state of the binary
with all the functions and their definitions.
"""

from __future__ import annotations

import atexit
import shutil
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests
import click

from binsize import BinarySize, get_sections_sizes, show_binaries_diff, set_root_dir

HERE = Path(__file__).parent
CORE_DIR = HERE.parent.parent

FIRMWARE_ELF = CORE_DIR / "build/firmware/firmware.elf"

MAX_KB_ADDITION_TO_SUCCEED = 5


def download_and_get_latest_master_firmware_elf() -> Path:
    url = "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/jobs/artifacts/main/download?job=core%20fw%20regular%20build"
    req = requests.get(url)
    tmp_dir = HERE / "tmp_for_master_elf"
    zip_file = ZipFile(BytesIO(req.content))
    zip_file.extractall(tmp_dir)

    atexit.register(lambda: shutil.rmtree(tmp_dir))

    return tmp_dir / "firmware.elf"


def generate_report_file(fw_location: str, report_file: str | Path) -> None:
    BinarySize().load_file(
        fw_location, sections=(".flash", ".flash2")
    ).add_basic_info().aggregate().sort(lambda row: row.size, reverse=True).show(
        report_file
    )


@click.command()
@click.argument("fw_location", required=False, default=FIRMWARE_ELF)
@click.option("-r", "--report-file", help="Report file")
def compare_master(fw_location: str, report_file: str | None) -> None:
    print(f"Analyzing {fw_location}")
    set_root_dir(str(CORE_DIR))

    if report_file:
        print(f"Generating report file under {report_file}")
        generate_report_file(fw_location, report_file)

    sections = (".flash", ".flash2")

    master_bin = download_and_get_latest_master_firmware_elf()
    if not master_bin.exists():
        print("Master firmware not found")
        sys.exit(1)

    show_binaries_diff(old=master_bin, new=fw_location, sections=sections)

    curr = get_sections_sizes(fw_location, sections)
    curr_flash = curr[".flash"] // 1024
    curr_flash_2 = curr[".flash2"] // 1024

    master = get_sections_sizes(master_bin, sections)
    master_flash = master[".flash"] // 1024
    master_flash_2 = master[".flash2"] // 1024

    print()
    print(f"Current: flash={curr_flash}K flash2={curr_flash_2}K")
    print(f"Master:  flash={master_flash}K flash2={master_flash_2}K")

    size_diff = (curr_flash + curr_flash_2) - (master_flash + master_flash_2)
    print(f"Size_diff: {size_diff} K")
    if size_diff > MAX_KB_ADDITION_TO_SUCCEED:
        print(f"Size of flash sections increased by {size_diff} K.")
        print(f"More than allowed {MAX_KB_ADDITION_TO_SUCCEED} K. Failing.")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    compare_master()
