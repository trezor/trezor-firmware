#!/usr/bin/env python3
import click

from trezorlib import cosi, firmware
from trezorlib._internal import firmware_headers

from typing import List, Tuple

# =========================== signing =========================


def sign_with_privkeys(digest: bytes, privkeys: List[bytes]) -> bytes:
    """Locally produce a CoSi signature."""
    pubkeys = [cosi.pubkey_from_privkey(sk) for sk in privkeys]
    nonces = [cosi.get_nonce(sk, digest, i) for i, sk in enumerate(privkeys)]

    global_pk = cosi.combine_keys(pubkeys)
    global_R = cosi.combine_keys(R for r, R in nonces)

    sigs = [
        cosi.sign_with_privkey(digest, sk, global_pk, r, global_R)
        for sk, (r, R) in zip(privkeys, nonces)
    ]

    signature = cosi.combine_sig(global_R, sigs)
    try:
        cosi.verify_combined(signature, digest, global_pk)
    except Exception as e:
        raise click.ClickException(f"Failed to produce valid signature.") from e

    return signature


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


# ===================== CLI actions =========================


def do_replace_vendorheader(fw, vh_file) -> None:
    if not isinstance(fw, firmware_headers.FirmwareImage):
        raise click.ClickException("Invalid image type (must be firmware).")

    vh = firmware.VendorHeader.parse(vh_file.read())
    if vh.header_len != fw.fw.vendor_header.header_len:
        raise click.ClickException("New vendor header must have the same size.")

    fw.fw.vendor_header = vh


@click.command()
@click.option("-n", "--dry-run", is_flag=True, help="Do not save changes.")
@click.option("-h", "--rehash", is_flag=True, help="Force recalculate hashes.")
@click.option("-v", "--verbose", is_flag=True, help="Show verbose info about headers.")
@click.option(
    "-S",
    "--sign-private",
    "privkey_data",
    multiple=True,
    help="Private key to use for signing.",
)
@click.option(
    "-D", "--sign-dev-keys", is_flag=True, help="Sign with development header keys."
)
@click.option(
    "-s", "--signature", "insert_signature", nargs=2, help="Insert external signature."
)
@click.option("-V", "--replace-vendor-header", type=click.File("rb"))
@click.option(
    "-d",
    "--digest",
    "print_digest",
    is_flag=True,
    help="Only output fingerprint for signing.",
)
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
):
    firmware_data = firmware_file.read()

    try:
        fw = firmware_headers.parse_image(firmware_data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        magic = firmware_data[:4]
        raise click.ClickException(
            f"Could not parse file (magic bytes: {magic!r})"
        ) from e

    digest = fw.digest()
    if print_digest:
        click.echo(digest.hex())
        return

    if replace_vendor_header:
        do_replace_vendorheader(fw, replace_vendor_header)

    if rehash:
        fw.rehash()

    if sign_dev_keys:
        privkeys = fw.DEV_KEYS
        sigmask = fw.DEV_KEY_SIGMASK
    else:
        sigmask, privkeys = parse_privkey_args(privkey_data)

    signature = None

    if privkeys:
        click.echo("Signing with local private keys...", err=True)
        signature = sign_with_privkeys(digest, privkeys)

    if insert_signature:
        click.echo("Inserting external signature...", err=True)
        sigmask_str, signature = insert_signature
        signature = bytes.fromhex(signature)
        sigmask = 0
        for bit in sigmask_str.split(":"):
            sigmask |= 1 << (int(bit) - 1)

    if signature:
        fw.rehash()
        fw.insert_signature(signature, sigmask)

    click.echo(fw.format(verbose))

    updated_data = fw.dump()
    if updated_data == firmware_data:
        click.echo("No changes made", err=True)
    elif dry_run:
        click.echo("Not saving changes", err=True)
    else:
        firmware_file.seek(0)
        firmware_file.truncate(0)
        firmware_file.write(updated_data)


if __name__ == "__main__":
    cli()
