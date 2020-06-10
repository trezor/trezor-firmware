#!/usr/bin/env python3
import click

from trezorlib import cosi, firmware
from trezorlib._internal import firmware_headers

from typing import List, Tuple


try:
    import Pyro4

    Pyro4.config.SERIALIZER = "marshal"
except ImportError:
    Pyro4 = None

PORT = 5001

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
        raise click.ClickException("Failed to produce valid signature.") from e

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
            click.echo("Could not parse key: {}".format(key))
            click.echo("Keys must be in the format: <key index>:<hex-encoded key>")
            raise click.ClickException("Unrecognized key format.")
    return sigmask, privkeys


def process_remote_signers(fw, addrs: List[str]) -> Tuple[int, List[bytes]]:
    if len(addrs) < fw.sigs_required:
        raise click.ClickException(
            "Not enough signers (need at least {})".format(fw.sigs_required)
        )

    digest = fw.digest()
    name = fw.NAME

    def mkproxy(addr):
        return Pyro4.Proxy("PYRO:keyctl@{}:{}".format(addr, PORT))

    sigmask = 0
    pks, Rs = [], []
    for addr in addrs:
        click.echo("Connecting to {}...".format(addr))
        with mkproxy(addr) as proxy:
            pk, R = proxy.get_commit(name, digest)
        if pk not in fw.public_keys:
            raise click.ClickException(
                "Signer at {} commits with unknown public key {}".format(addr, pk.hex())
            )
        idx = fw.public_keys.index(pk)
        click.echo(
            "Signer at {} commits with public key #{}: {}".format(
                addr, idx + 1, pk.hex()
            )
        )
        sigmask |= 1 << idx
        pks.append(pk)
        Rs.append(R)

    # compute global commit
    global_pk = cosi.combine_keys(pks)
    global_R = cosi.combine_keys(Rs)

    # collect signatures
    sigs = []
    for addr in addrs:
        click.echo("Waiting for {} to sign... ".format(addr), nl=False)
        with mkproxy(addr) as proxy:
            sig = proxy.get_signature(name, digest, global_R, global_pk)
        sigs.append(sig)
        click.echo("OK")

    for addr in addrs:
        with mkproxy(addr) as proxy:
            proxy.finish()

    # compute global signature
    return sigmask, cosi.combine_sig(global_R, sigs)


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
@click.option(
    "-r",
    "--remote",
    metavar="IPADDR",
    multiple=True,
    help="IP address of remote signer. Can be repeated.",
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
    remote,
):
    """Manage trezor-core firmware headers.

    This tool supports three types of files: raw vendor headers (TRZV), bootloader
    images (TRZB), and firmware images which are prefixed with a vendor header
    (TRZV+TRZF).

    Run with no options on a file to dump information about that file.

    Run with -d to print the header digest and exit. This works correctly regardless of
    whether code hashes have been filled.

    Run with -h to recalculate and fill in code hashes.

    To insert an external signature:

      ./headertool.py firmware.bin -s 1:2:3 ABCDEF<...signature in hex format>

    The string "1:2:3" is a list of 1-based indexes of keys used to generate the signature.

    To sign with local private keys:

    \b
      ./headertool.py firmware.bin -S 1:ABCDEF<...hex private key> -S 2:1234<..hex private key>

    Each instance of -S is in the form "index:privkey", where index is the same as
    above. Instead of specifying the keys manually, use -D to substitue known
    development keys.

    Signature validity is not checked in either of the two cases.

    To sign with remote participants:

      ./headertool.py firmware.bin -r 10.24.13.11 -r 10.24.13.190 ...

    Each participant must be running keyctl-proxy configured on the same file. Signers'
    public keys must be in the list of known signers and are matched to indexes
    automatically.
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

    if remote:
        if Pyro4 is None:
            raise click.ClickException("Please install Pyro4 for remote signing.")
        click.echo(fw.format())
        click.echo("Signing with {} remote participants.".format(len(remote)))
        sigmask, signature = process_remote_signers(fw, remote)

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
