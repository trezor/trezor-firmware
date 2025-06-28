#!/usr/bin/env python3
import time
from pathlib import Path
import sys

import click
import serial

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

def upload_nrf(port, bin_path, chunk_size):
    # Read binary file
    data = Path(bin_path).read_bytes()
    total = len(data)
    click.echo(f"Read {total} bytes from {bin_path!r}")

    # Open USB-VCP port
    ser = serial.Serial(port, timeout=2)
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # 1) Begin transfer
    send_cmd(ser, "nrf-update begin")

    # 2) Stream chunks
    offset = 0
    while offset < total:
        chunk = data[offset:offset + chunk_size]
        hexstr = chunk.hex()
        send_cmd(ser, f"nrf-update chunk {hexstr}")
        offset += len(chunk)
        pct = offset * 100 // total
        click.echo(f"  Uploaded {offset}/{total} bytes ({pct}%)")

    # 3) Finish transfer
    send_cmd(ser, "nrf-update end")
    click.echo("nRF update complete.")

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument("binary", metavar="<nrf-binary>", type=click.Path(exists=True, dir_okay=False))
@click.option("--chunk-size", "-c", default=512, show_default=True,
              help="Max bytes per chunk")
def main(port, binary, chunk_size):
    """
    Upload an nRF firmware image via USB-VCP CLI.

    <serial-port> e.g. /dev/ttyUSB0 or COM3
    <nrf-binary> path to the .bin file
    """
    try:
        upload_nrf(port, binary, chunk_size)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
