#!/usr/bin/env python3
import sys
import time
import zlib
from pathlib import Path

import click
import serial


def compress_binary(data: bytes) -> bytes:
    """
    Compress data with zlib at max compression, raw deflate.
    """
    compressor = zlib.compressobj(level=9, wbits=-10)
    return compressor.compress(data) + compressor.flush()


def exit_interactive_mode(ser: serial.Serial) -> None:
    ser.write(("." + "\r\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer()


def send_cmd(ser: serial.Serial, cmd: str, expect_ok: bool = True) -> str:
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


def upload_bootloader(port: str, bin_path: str, chunk_size: int) -> None:
    # Read binary file
    data = Path(bin_path).read_bytes()
    data_size = len(data)
    click.echo(f"Read {data_size} bytes from {bin_path!r}")

    if data[:4] == b"TRZB":
        compress = True
    elif data[:4] == b"TRZQ":
        compress = False
    else:
        click.echo("Invalid bootloader binary.", err=True)
        sys.exit(1)

    # Compress the data
    if compress:
        comp_data = compress_binary(data)
        comp_size = len(comp_data)
        click.echo(
            f"Compressed to {comp_size} bytes ({comp_size * 100 // data_size}% of original)"
        )
        data = comp_data
        data_size = comp_size

    # Open USB-VCP port
    with serial.Serial(port, timeout=2) as ser:
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        exit_interactive_mode(ser)

        # 1) Begin transfer
        send_cmd(ser, "bootloader-update begin")

        # 2) Stream data chunks
        offset = 0
        while offset < data_size:
            chunk = data[offset : offset + chunk_size]
            hexstr = chunk.hex()
            send_cmd(ser, f"bootloader-update chunk {hexstr}")
            offset += len(chunk)
            pct = offset * 100 // data_size
            click.echo(f"  Uploaded {offset}/{data_size} bytes ({pct}%)")

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
def main(port: str, binary: str, chunk_size: int) -> None:
    """
    Upload a bootloader image via USB-VCP CLI.

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
