#!/usr/bin/env python3
import sys
import time
from pathlib import Path

import click
import serial

UPDATE_TYPES = {
    "boardloader": {
        "command": "boardloader-update",
        "success_message": "Boardloader update complete.",
    },
    "nrf": {"command": "nrf-update", "success_message": "nRF update complete."},
}


def exit_interactive_mode(ser):
    ser.write(("." + "\r\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer()


def send_cmd(ser, cmd, expect_ok=True):
    """Send a line, read response, and abort on non-OK."""
    ser.write((cmd + "\r\n").encode())
    # Give the device a moment to process
    time.sleep(0.05)
    resp = ser.readline().decode(errors="ignore").strip()
    # Skip comments or empty lines
    while resp.startswith("#") or len(resp) == 0:
        resp = ser.readline().decode(errors="ignore").strip()
    click.echo(f"> {cmd}")
    click.echo(f"< {resp}")
    if expect_ok and not resp.startswith("OK"):
        click.echo("Error from device, aborting.", err=True)
        sys.exit(1)
    return resp


def upload_binary(port, bin_path, chunk_size, update_type):
    if update_type not in UPDATE_TYPES:
        raise ValueError(
            f"Invalid update type. Must be one of: {', '.join(UPDATE_TYPES.keys())}"
        )

    # Read binary file
    data = Path(bin_path).read_bytes()
    total = len(data)
    click.echo(f"Read {total} bytes from {bin_path!r}")

    update_config = UPDATE_TYPES[update_type]
    command = update_config["command"]

    # Open USB-VCP port using context manager
    with serial.Serial(port, timeout=2) as ser:
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        exit_interactive_mode(ser)

        # 1) Begin transfer
        send_cmd(ser, f"{command} begin")

        # 2) Stream chunks
        offset = 0
        while offset < total:
            chunk = data[offset : offset + chunk_size]
            hexstr = chunk.hex()
            send_cmd(ser, f"{command} chunk {hexstr}")
            offset += len(chunk)
            pct = offset * 100 // total
            click.echo(f"  Uploaded {offset}/{total} bytes ({pct}%)")

        # 3) Finish transfer
        send_cmd(ser, f"{command} end")
        click.echo(update_config["success_message"])


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument(
    "binary", metavar="<binary>", type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    "--chunk-size", "-c", default=512, show_default=True, help="Max bytes per chunk"
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(list(UPDATE_TYPES.keys()), case_sensitive=False),
    required=True,
    help="Type of update to perform",
)
def main(port, binary, chunk_size, type):
    """
    Upload a firmware image via USB-VCP CLI.

    <serial-port> e.g. /dev/ttyUSB0 or COM3
    <binary> path to the .bin file
    """
    try:
        upload_binary(port, binary, chunk_size, type)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
