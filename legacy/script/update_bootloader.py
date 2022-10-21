#!/usr/bin/env python3
from __future__ import annotations

import typing as t
from hashlib import sha256
from pathlib import Path

import click

LEGACY_ROOT = Path(__file__).parent.parent.resolve()

BOOTLOADER_BUILT = LEGACY_ROOT / "bootloader" / "bootloader.bin"
BOOTLOADER_IMAGE = LEGACY_ROOT / "firmware" / "bootloader.dat"

BOOTLOADER_VERSION = LEGACY_ROOT / "bootloader" / "version.h"
FIRMWARE_VERSION = LEGACY_ROOT / "firmware" / "version.h"

BL_CHECK_C = LEGACY_ROOT / "firmware" / "bl_check.c"
BL_CHECK_TXT = LEGACY_ROOT / "firmware" / "bl_check.txt"

BL_CHECK_PATTERN = """\
  if (0 ==
      memcmp(hash,
             {line1}
             {line2},
             32))
    return 1;  // {comment}
"""

BL_CHECK_AUTO_BEGIN = "  // BEGIN AUTO-GENERATED BOOTLOADER ENTRIES (bl_check.txt)\n"
BL_CHECK_AUTO_END = "  // END AUTO-GENERATED BOOTLOADER ENTRIES (bl_check.txt)\n"


def cstrify(data: bytes) -> str:
    """Convert bytes to C string literal.

    >>> cstrify(b"foo")
    '"\\x66\\x6f\\x6f"'
    """
    return '"' + "".join(rf"\x{b:02x}" for b in data) + '"'


def load_version(filename: Path) -> str:
    """Load version from version.h"""
    vdict = {}
    with open(filename) as f:
        for line in f:
            if line.startswith("#define VERSION_"):
                _define, symbol, value = line.split()
                _, name = symbol.lower().split("_", maxsplit=1)
                vdict[name] = int(value)

    return "{major}.{minor}.{patch}".format(**vdict)


def load_hash_entries() -> dict[bytes, str]:
    """Load hash entries from bl_check.txt"""
    return {
        bytes.fromhex(digest): comment
        for digest, comment in (
            line.split(" ", maxsplit=1)
            for line in BL_CHECK_TXT.read_text().splitlines()
        )
    }


def regenerate_bl_check(hash_entries: t.Iterable[tuple[bytes, str]]) -> None:
    """Regenerate bl_check.c with given hash entries."""
    bl_check_new = []
    with open(BL_CHECK_C) as f:
        # read up to AUTO-BEGIN
        for line in f:
            bl_check_new.append(line)
            if line == BL_CHECK_AUTO_BEGIN:
                break

        # generate new sections
        for digest, comment in hash_entries:
            bl_check_new.append(
                BL_CHECK_PATTERN.format(
                    line1=cstrify(digest[:16]),
                    line2=cstrify(digest[16:]),
                    comment=comment,
                )
            )

        # consume up to AUTO-END
        for line in f:
            if line == BL_CHECK_AUTO_END:
                bl_check_new.append(line)
                break

        # add rest of the file contents
        bl_check_new.extend(f)

    BL_CHECK_C.write_text("".join(bl_check_new))


@click.command()
@click.option("-c", "--comment", help="Comment for the hash entry.")
def main(comment: str | None) -> None:
    """Insert a new bootloader image.

    Takes bootloader/boootloader.dat, copies over firmware/bootloader.dat, and adds
    an entry to firmware/bl_check.txt and bl_check.c
    """
    bl_bytes = BOOTLOADER_BUILT.read_bytes()
    digest = sha256(sha256(bl_bytes).digest()).digest()
    click.echo("Bootloader digest: " + digest.hex())

    entries = load_hash_entries()
    if digest in entries:
        click.echo("Bootloader already in bl_check.txt: " + entries[digest])

    else:
        if comment is None:
            bl_version = load_version(BOOTLOADER_VERSION)
            fw_version = load_version(FIRMWARE_VERSION)
            comment = f"{bl_version} shipped with fw {fw_version}"

        # insert new bootloader
        with open(BL_CHECK_TXT, "a") as f:
            f.write(f"{digest.hex()} {comment}\n")

        entries[digest] = comment
        click.echo("Inserted new entry: " + comment)
    
    # rewrite bl_check.c
    regenerate_bl_check(entries.items())
    click.echo("Regenerated bl_check.c")

    # overwrite bootloader.dat
    BOOTLOADER_IMAGE.write_bytes(bl_bytes)
    click.echo("Installed bootloader.dat into firmware")


if __name__ == "__main__":
    main()
