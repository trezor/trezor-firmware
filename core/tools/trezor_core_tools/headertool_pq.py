#!/usr/bin/env python3
import click

from trezorlib._internal import firmware_headers


def no_echo(*args, **kwargs):
    """A no-op function to replace click.echo when quiet mode is enabled."""
    pass


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
    firmware_file,
    verbose,
    dry_run,
    sign_dev_keys,
    merkle_proof,
    print_merkle_root,
    quiet,
):
    """Manage firmware headers.

    This tool supports new bootloader header (TRZQ) with PQC signature. Other
    legacy images are still supported by headertool.py.

    Run with no options on a file to dump information about that file.

    Run with -d to print the header digest and exit. This works correctly regardless of
    whether code hashes have been filled.

    """
    firmware_data = firmware_file.read()

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
