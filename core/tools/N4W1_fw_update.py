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

def tm_ok(resp):
    return resp == "OK"

def exit_interactive_mode(ser: serial.Serial) -> None:
    ser.write(("." + "\r\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer() 

def send_ctrl_c(ser: serial.Serial) -> None:
    """Send Ctrl+C (ASCII ETX, 0x03) to abort the current CLI command."""
    ser.write(b"\x03")
    time.sleep(0.05)
    ser.reset_input_buffer()

def send_cmd(ser: serial.Serial, cmd: str) -> str:
    """Send a line and return the first non-empty response line."""
    ser.reset_input_buffer()

    click.echo(f"> {cmd}")
    ser.write((cmd + "\r\n").encode())
    # Give the device a moment to process
    time.sleep(0.05)

    resp = ""
    for _ in range(20):
        resp = ser.readline().decode(errors="ignore").strip()
        if resp:
            break

    click.echo(f"< {resp}")
    return resp

def wait_for_line(ser: serial.Serial, expected: str) -> None:
    """Read lines until one contains expected."""
    while True:
        resp = ser.readline().decode(errors="ignore").strip()
        click.echo(f"{resp}")
        if expected in resp:
            break


# Wrappers for the nfc-backup-transparent-mode command set (see
# nfc_backup_tm_cmds in prodtest_nfc_backup.c).
def tm_on(ser: serial.Serial) -> str:
    return send_cmd(ser, "on")


def tm_off(ser: serial.Serial) -> str:
    return send_cmd(ser, "off")


def tm_reset(ser: serial.Serial) -> str:
    return send_cmd(ser, "reset")


def tm_noise(ser: serial.Serial) -> str:
    return send_cmd(ser, "noise")


def tm_transceive(ser: serial.Serial, hex_data: str) -> str:
    return send_cmd(ser, f"transceive {hex_data}")


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

        # Turn ON the NFC 
        tm_on(ser)
        
        # wait for connected card
        wait_for_line(ser, "NFC card connected.")

        tic = time.time()

        # Start the binary flash process and read which bank should get dirty
        resp = tm_transceive(ser, "80100000")

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

        chunk_size = 480
        total_chunks = (len(bin_bytes) + chunk_size - 1) // chunk_size
        for i in range(0, len(bin_bytes), chunk_size):
            chunk = bin_bytes[i : i + chunk_size]
            if len(chunk) <= 255:
                # Short APDU Lc encoding: [CLA INS P1 P2 Lc Data]
                lc = f"{len(chunk):02x}"
            else:
                # Extended APDU Lc encoding: [CLA INS P1 P2 00 LcHi LcLo Data]
                lc = "00" + f"{len(chunk):04x}"
            resp = tm_transceive(ser, "80110000" + lc + chunk.hex())
            if not resp_ok(resp):
                panic("Unable to upload binary chunk")
            click.echo(f"Uploaded chunk {i // chunk_size + 1}/{total_chunks}")

        # Finish the binary upload
        resp = tm_transceive(ser, "8012000000")

        toc = time.time()

        if resp_ok(resp):
            click.echo("Binary upload completed successfully.")
        else:
            panic("binary upload failed")

        click.echo(f"Upload took {toc - tic:.2f} seconds")

        # Reset the card
        if not tm_ok(tm_reset(ser)):
            panic("Unable to reset NFC")

        # wait for connected card
        wait_for_line(ser, "NFC card connected.")

        resp = tm_transceive(ser, "80140000")
        if resp_ok(resp):
            click.echo("Firmware bank switched successfully.")
        else: 
            panic("Unable to switch firmware bank")

        # Reset the card
        if not tm_ok(tm_reset(ser)):
            panic("Unable to reset NFC")

        # Start the binary flash process and read which bank should get dirty
        resp = tm_transceive(ser, "80100000")

        tm_off(ser)

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
