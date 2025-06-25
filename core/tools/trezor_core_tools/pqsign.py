#!/usr/bin/env python3
import click

from trezorlib._internal import firmware_headers
from slhdsa import sha2_128s, SecretKey

# Development keys for signing
PRIVATE_KEY_DEV = bytes.fromhex(
    "9a8da9d38eb9203bd0d5442db161324f35ce7f6dc78e05507306fb13a7e6c145"
    "ec01e60263024f7e71728013b731f7ba1299f518c27ba3ed8f4a219974127c62")

PUBLIC_KEY_DEV = bytes.fromhex(
    "ec01e60263024f7e71728013b731f7ba1299f518c27ba3ed8f4a219974127c62")

# Signature block definition
BOOTHEADER_SIZE = 16384
BOOTHEADER_SIGNATURE_OFFSET = 640

@click.command()
@click.argument("bootloader_file", type=click.File("rb+"))
@click.argument("bootheader_file", type=click.File("wb+"))
def cli(
    bootloader_file,
    bootheader_file
):
    bootloader_image = bootloader_file.read()

    try:
        bl = firmware_headers.parse_image(bootloader_image)
    except Exception as e:
        magic = bootloader_image[:4]
        raise click.ClickException(
            "Could not parse file (magic bytes: {!r})".format(magic)
        ) from e

    # Load the key for signing
    key = SecretKey.from_digest(PRIVATE_KEY_DEV, sha2_128s)

    # Sign bootloader iamge
    data_to_sign = bootloader_image[:bl.header.header_len]
    pq_signature = key.sign(data_to_sign)

    # Create the bootheader
    bootheader = b''
    bootheader += bytes(BOOTHEADER_SIGNATURE_OFFSET)
    bootheader += bytes(pq_signature)
    bootheader += bytes(BOOTHEADER_SIZE - len(bootheader))

    bootheader_file.write(bootheader)

if __name__ == "__main__":
    cli()
