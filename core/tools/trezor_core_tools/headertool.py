#!/usr/bin/env python3
import click

from trezorlib import cosi, firmware
from trezorlib._internal import firmware_headers

from typing import List, Sequence, Tuple

# =========================== signing =========================


def parse_privkey_args(privkey_data: List[str]) -> Tuple[int, List[bytes]]:
    privkeys = []
    sigmask = 0
    for key in privkey_data:
        try:
            idx, key_hex = key.split(":", maxsplit=1)
            privkeys.append(bytes.fromhex(key_hex))
            sigmask |= 1 << (int(idx) - 1)
        except ValueError:
            click.echo(f"Could not parse key: {key}")
            click.echo("Keys must be in the format: <key index>:<hex-encoded key>")
            raise click.ClickException("Unrecognized key format.")
    return sigmask, privkeys


def do_rehash(fw: firmware_headers.SignableImageProto) -> None:
    """Recalculate the code hashes inside the header."""
    if isinstance(fw, firmware.FirmwareImage):
        fw.header.hashes = fw.code_hashes()
    elif isinstance(fw, firmware_headers.VendorFirmware):
        fw.firmware.header.hashes = fw.firmware.code_hashes()
    # else: do nothing, other kinds of images do not need rehashing


# ===================== CLI actions =========================


def do_replace_vendorheader(fw, vh_file) -> None:
    if not isinstance(fw, firmware_headers.VendorFirmware):
        raise click.ClickException("Invalid image type (must be firmware).")

    vh = firmware.VendorHeader.parse(vh_file.read())
    if vh.header_len != fw.vendor_header.header_len:
        raise click.ClickException("New vendor header must have the same size.")

    fw.vendor_header = vh


@click.command()
@click.option("-n", "--dry-run", is_flag=True, help="Do not save changes.")
@click.option("-h", "--rehash", is_flag=True, help="Force recalculate hashes.")
@click.option("-v", "--verbose", is_flag=True, help="Show verbose info about headers.")
@click.option(
    "-S",
    "--sign-private",
    "privkey_data",
    metavar="INDEX:PRIVKEY_HEX",
    multiple=True,
    help="Private key to use for signing. Can be repeated.",
)
@click.option(
    "-D", "--sign-dev-keys", is_flag=True, help="Sign with development header keys."
)
@click.option(
    "-s",
    "--signature",
    "insert_signature",
    nargs=2,
    metavar="INDEX:INDEX:INDEX... SIGNATURE_HEX",
    help="Insert external signature.",
)
@click.option("-V", "--replace-vendor-header", type=click.File("rb"))
@click.option(
    "-d",
    "--digest",
    "print_digest",
    is_flag=True,
    help="Only output header digest for signing and exit.",
)
@click.option("-q", "--quiet", is_flag=True, help="Do not print anything.")
@click.argument("firmware_file", type=click.File("rb+"))
def cli(
    firmware_file,
    verbose,
    rehash,
    dry_run,
    privkey_data,
    sign_dev_keys,
    insert_signature,
    replace_vendor_header,
    print_digest,
    quiet,
):
    """Manage firmware headers.

    This tool supports three types of files: raw vendor headers (TRZV), bootloader
    images (TRZB), and firmware images which are prefixed with a vendor header
    (TRZV+TRZF).

    Run with no options on a file to dump information about that file.

    Run with -d to print the header digest and exit. This works correctly regardless of
    whether code hashes have been filled.

    Run with -h to recalculate and fill in code hashes.

    To insert an external signature:

      headertool firmware.bin -s 1:2:3 ABCDEF<...signature in hex format>

    The string "1:2:3" is a list of 1-based indexes of keys used to generate the signature.

    To sign with local private keys:

    \b
      headertool firmware.bin -S 1:ABCDEF<...hex private key> -S 2:1234<..hex private key>

    Each instance of -S is in the form "index:privkey", where index is the same as
    above. Instead of specifying the keys manually, use -D to substitue known
    development keys.

    Signature validity is not checked in either of the two cases.
    """
    firmware_data = firmware_file.read()

    try:
        fw = firmware_headers.parse_image(firmware_data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        magic = firmware_data[:4]
        raise click.ClickException(
            "Could not parse file (magic bytes: {!r})".format(magic)
        ) from e

    digest = fw.digest()
    if print_digest:
        click.echo(digest.hex())
        return

    if quiet:
        echo = lambda *args, **kwargs: None
    else:
        echo = click.echo

    if replace_vendor_header:
        do_replace_vendorheader(fw, replace_vendor_header)

    if sign_dev_keys:
        if not isinstance(fw, firmware_headers.CosiSignedImage):
            raise click.ClickException("Can't use development keys on this image type.")
        privkeys = fw.DEV_KEYS
        sigmask = (1 << len(privkeys)) - 1
    else:
        sigmask, privkeys = parse_privkey_args(privkey_data)

    signature = None

    if privkeys:
        echo("Signing with local private keys...", err=True)
        signature = cosi.sign_with_privkeys(digest, privkeys)

    if insert_signature:
        echo("Inserting external signature...", err=True)
        sigmask_str, signature = insert_signature
        signature = bytes.fromhex(signature)
        sigmask = 0
        for bit in sigmask_str.split(":"):
            sigmask |= 1 << (int(bit) - 1)

    if signature:
        if not isinstance(fw, firmware_headers.CosiSignedImage):
            raise click.ClickException("Can't sign this image type.")
        fw.insert_signature(signature, sigmask)

    if signature or rehash:
        do_rehash(fw)

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
