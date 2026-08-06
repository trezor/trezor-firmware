#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, BinaryIO

import click

from trezorlib._internal import firmware_headers

from . import firmware_module


def no_echo(*args: Any, **kwargs: Any) -> None:
    """A no-op function to replace click.echo when quiet mode is enabled."""
    pass


def _fill_module_image(
    firmware_file: BinaryIO,
    firmware_data: bytes,
    dry_run: bool,
    print_merkle_root: bool,
    echo: Any,
) -> None:
    """Fill the manifest code hashes of a Merkle-tree firmware image.

    This is the build-time step for `firmware.bin`: each manifest directory
    entry's `code_hash` (single SHA-256 over the module code at addr..addr+size)
    is filled -- ALWAYS the real code hash, including a CUSTOM variant's
    kernel+coreapp (its real hash is the creator's integrity hash). The
    firmware_root is derived later (by the tree signer) from the filled image;
    for the custom variant the signer zeroes the app hash only for the
    authenticity leaf (variant_leaf), never on flash. The variant (incl. CUSTOM)
    is baked into the manifest at build time, not chosen here.
    """
    fw = bytearray(firmware_data)

    # Patch the manifest template (from manifest_header.S) at the image start:
    # fill each entry's code_hash from the placed module code (module_type /
    # flags / addr / size are already set by the .S).
    firmware_module.fill_manifest(fw)

    manifest = firmware_module.read_manifest(fw)
    leaf = firmware_module.variant_leaf(manifest)

    if print_merkle_root:
        click.echo(leaf.hex())
        return

    entries = firmware_module.manifest_entries(fw)
    echo(f"Detected image type: firmware manifest (TRZD), {len(entries)} modules")
    # Show the FILLED manifest (post-fill), so build-time output has the real
    # addr/size/code_hash values -- not the unfilled template.
    echo(firmware_module.format_manifest(manifest))
    if firmware_module.is_custom_firmware(fw):
        echo(
            "CUSTOM (unofficial) variant: kernel+coreapp is founder-UNbound "
            "(integrity-only); installs unprivileged, unlocked-bootloader-only."
        )
    # The variant leaf = H(0x00 || manifest); the founder firmware_root that spans
    # all variants is derived later by the signer.
    echo(f"variant leaf   : {leaf.hex()}")

    if bytes(fw) == firmware_data:
        echo("No changes made", err=True)
    elif dry_run:
        echo("Not saving changes", err=True)
    else:
        firmware_file.seek(0)
        firmware_file.truncate(0)
        firmware_file.write(fw)


@click.command()
@click.option("-n", "--dry-run", is_flag=True, help="Do not save changes.")
@click.option("-v", "--verbose", is_flag=True, help="Show verbose info about headers.")
@click.option(
    "-D", "--sign-dev-keys", is_flag=True, help="Sign with development header keys."
)
@click.option(
    "-m",
    "--merkle-root",
    "print_merkle_root",
    is_flag=True,
    help="Only output Merkle root for signing and exit.",
)
@click.option(
    "-M",
    "--merkle-proof",
    "merkle_proof",
    multiple=True,
    help="Merkle proof node. Can be repeated.",
)
@click.option("-q", "--quiet", is_flag=True, help="Do not print anything.")
@click.argument("firmware_file", type=click.File("rb+"))
def cli(
    firmware_file: BinaryIO,
    verbose: bool,
    dry_run: bool,
    sign_dev_keys: bool,
    merkle_proof: list[str],
    print_merkle_root: bool,
    quiet: bool,
) -> None:
    """Manage firmware headers.

    This tool supports new bootloader header (TRZQ) with PQC signature. Other
    legacy images are still supported by headertool.py.

    Run with no options on a file to dump information about that file.

    Run with -d to print the header digest and exit. This works correctly regardless of
    whether code hashes have been filled.

    """
    firmware_data = firmware_file.read()

    # Merkle-tree firmware image: fill the per-module code hashes in the manifest
    # in place. This is the build step for firmware.bin; the firmware_root is
    # folded into the bootloader header later by the tree signer. Detection: the
    # image starts with the manifest ('TRZD') at offset 0 (emitted by
    # manifest_header.S, even on a fresh build before code_hash fill).
    is_tree = firmware_data[:4] == firmware_module.MANIFEST_MAGIC
    if is_tree:
        if quiet:
            echo = no_echo
        else:
            echo = click.echo
        _fill_module_image(
            firmware_file,
            firmware_data,
            dry_run,
            print_merkle_root,
            echo,
        )
        return

    try:
        fw = firmware_headers.BootloaderV2Image.parse(firmware_data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        magic = firmware_data[:4]
        raise click.ClickException(
            f"Could not parse file (magic bytes: {magic})"
        ) from e

    fw.set_merkle_proof(list(map(bytes.fromhex, merkle_proof)))

    if print_merkle_root:
        click.echo(fw.merkle_root().hex())
        return

    if quiet:
        echo = no_echo
    else:
        echo = click.echo

    if sign_dev_keys:
        echo("Signing with dev keys...", err=True)
        fw.sign_with_devkeys()

    echo(f"Detected image type: {fw.NAME}")
    echo(fw.format(verbose))

    updated_data = fw.build()
    if updated_data == firmware_data:
        echo("No changes made", err=True)
    elif dry_run:
        echo("Not saving changes", err=True)
    else:
        firmware_file.seek(0)
        firmware_file.truncate(0)
        firmware_file.write(updated_data)


if __name__ == "__main__":
    cli()
