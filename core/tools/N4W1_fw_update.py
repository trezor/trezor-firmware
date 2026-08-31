#!/usr/bin/env python3
import sys
import time
from pathlib import Path

import click
import serial

def panic(err_msg : str):
    click.echo(f"panic: {str}")
    sys.exit(1)

def resp_ok(resp):
    return resp.endswith("9000")

def exit_interactive_mode(ser: serial.Serial) -> None:
    ser.write(("." + "\r\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer() 

def send_cmd(ser: serial.Serial, cmd: str) -> str:
    """Send a line, read response, and abort on CLI_ERROR."""
    ser.reset_input_buffer()

    click.echo(f"{cmd}")
    ser.write((cmd + "\r\n").encode())
    # Give the device a moment to process
    time.sleep(0.05)

    resp = ser.readline().decode(errors="ignore").strip()
    click.echo(f"{resp}")
    return resp

def find_bank_binary(binary_dir: Path, suffix: str) -> Path:
    matches = sorted(binary_dir.glob(f"*{suffix}"))
    if not matches:
        click.echo(f"No binary ending with {suffix!r} found in {binary_dir}", err=True)
        sys.exit(1)
    return matches[0]


def parse_binary(binary_path: Path) -> bytearray:
    return bytearray(Path(binary_path).read_bytes())


def run(port: str, binary_dir: str) -> None:
    bin_dir = Path(binary_dir)

    bank0_bin = find_bank_binary(bin_dir, "app-0.bin")
    bank1_bin = find_bank_binary(bin_dir, "app-1.bin")
    click.echo(f"Bank 0 binary: {bank0_bin}")
    click.echo(f"Bank 1 binary: {bank1_bin}")

    # Open USB-VCP port
    with serial.Serial(port, timeout=2) as ser:

        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        exit_interactive_mode(ser)

        send_cmd(ser, "nfc-backup-transparent-mode")

        # Start the binary flash process and read which bank should get dirty
        resp = send_cmd(ser, "80100000")

        bin_bytes = []
        if resp_ok(resp):

            if resp.startswith("01"):
                click.echo("Firmware will be uploaded to bank 1")
                bin_bytes = parse_binary(bank1_bin)
            elif resp.startswith("00"):
                click.echo("Firmware will be uploaded to bank 0")
                bin_bytes = parse_binary(bank0_bin)
            else:
                panic("unexpected bank number")
        else:
            panic("Unable to start the binary upload")

        chunk_size = 256
        total_chunks = (len(bin_bytes) + chunk_size - 1) // chunk_size
        for i in range(0, len(bin_bytes), chunk_size):
            chunk = bin_bytes[i : i + chunk_size]
            resp = send_cmd(ser, "80110000" + chunk.hex())
            if not resp_ok(resp):
                panic("Unable to upload binary chunk")
            click.echo(f"Uploaded chunk {i // chunk_size + 1}/{total_chunks}")



@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument(
    "binary_dir",
    metavar="<binary-dir>",
    type=click.Path(exists=True, file_okay=False),
)
def main(port: str, binary_dir: str) -> None:
    """
    <serial-port> e.g. /dev/ttyUSB0 or COM3
    <binary-dir> path to the folder containing the app-0.bin and app-1.bin firmware binaries
    """
    try:
        run(port, binary_dir)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
