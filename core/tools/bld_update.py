#!/usr/bin/env python3
import sys
import time
import zlib
from pathlib import Path

import click
import serial


def _compress(data: bytes) -> bytes:
    """
    Compress data with zlib at max compression, raw deflate.
    """
    compressor = zlib.compressobj(level=9, wbits=-10)
    return compressor.compress(data) + compressor.flush()


def send_cmd(ser, cmd, expect_ok=True):
    """Send a line, read response, and abort on CLI_ERROR."""
    ser.write((cmd + "\r\n").encode())
    # Give the device a moment to process
    time.sleep(0.05)
    resp = ser.readline().decode(errors="ignore").strip()
    while resp.startswith("#") or len(resp) == 0:
        resp = ser.readline().decode(errors="ignore").strip()
    click.echo(f"> {cmd}")
    click.echo(f"< {resp}")
    if expect_ok and not resp.startswith("OK"):
        click.echo("Error from device, aborting.", err=True)
        sys.exit(1)
    return resp


def upload_bootloader(port, bin_path, chunk_size):
    # Read binary file
    data = Path(bin_path).read_bytes()
    orig_size = len(data)
    click.echo(f"Read {orig_size} bytes from {bin_path!r}")

    # Compress the data
    comp_data = _compress(data)
    comp_size = len(comp_data)
    click.echo(
        f"Compressed to {comp_size} bytes ({comp_size * 100 // orig_size}% of original)"
    )

    # Open USB-VCP port
    ser = serial.Serial(port, timeout=2)
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # 1) Begin transfer
    send_cmd(ser, "bootloader-update begin")

    # 2) Stream compressed chunks
    offset = 0
    while offset < comp_size:
        chunk = comp_data[offset : offset + chunk_size]
        hexstr = chunk.hex()
        send_cmd(ser, f"bootloader-update chunk {hexstr}")
        offset += len(chunk)
        pct = offset * 100 // comp_size
        click.echo(f"  Uploaded {offset}/{comp_size} bytes ({pct}%)")

    # 3) Finish transfer
    send_cmd(ser, "bootloader-update end")
    click.echo("Bootloader upload complete.")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument(
    "binary",
    metavar="<bootloader-binary>",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--chunk-size",
    "-c",
    default=512,
    show_default=True,
    help="Max bytes per chunk (in compressed form)",
)
def main(port, binary, chunk_size):
    """
    Upload a (compressed) bootloader image via USB-VCP CLI.

    <serial-port> e.g. /dev/ttyUSB0 or COM3
    <bootloader-binary> path to the .bin file
    """
    try:
        upload_bootloader(port, binary, chunk_size)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
