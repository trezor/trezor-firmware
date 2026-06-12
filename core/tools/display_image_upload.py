#!/usr/bin/env python3
"""Upload an image to prodtest display over serial.

Example:
    python core/tools/display_image_upload.py /dev/ttyACM1 photo.jpg \\
        --width 240 --height 320
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import click
import serial

try:
    from serial.tools import list_ports
except Exception:
    list_ports = None

from display_image_converter import image_to_rgb565_le

# CLI line buffer is 8192 bytes; each raw byte → 2 hex chars; overhead = 21 bytes.
_MAX_CHUNK_BYTES = 4085


def exit_interactive_mode(ser: serial.Serial) -> None:
    ser.write(("." + "\r\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer()


def _format_cmd_for_log(cmd: str) -> str:
    if len(cmd) <= 120:
        return cmd
    return f"{cmd[:80]}... <{len(cmd)} chars>"


def send_cmd(ser: serial.Serial, cmd: str, expect_ok: bool = True) -> tuple[str, int]:
    """Send a line, read response, and abort on CLI_ERROR."""
    written = ser.write((cmd + "\r\n").encode()) or 0
    time.sleep(0.05)
    resp = ser.readline().decode(errors="ignore").strip()
    while resp.startswith("#") or len(resp) == 0:
        resp = ser.readline().decode(errors="ignore").strip()
    click.echo(f"> {_format_cmd_for_log(cmd)}")
    click.echo(f"< {resp}")
    if expect_ok and not resp.startswith("OK"):
        click.echo("Error from device, aborting.", err=True)
        sys.exit(1)
    return resp, written


def _serial_port_metadata(port: str) -> str:
    if list_ports is None:
        return "metadata unavailable (serial.tools.list_ports missing)"
    for info in list_ports.comports():
        if info.device == port:
            vid = f"0x{info.vid:04x}" if info.vid is not None else "n/a"
            pid = f"0x{info.pid:04x}" if info.pid is not None else "n/a"
            return (
                f"VID:PID={vid}:{pid} sn={info.serial_number or 'n/a'} "
                f"mfg={info.manufacturer or 'n/a'} product={info.product or 'n/a'} "
                f"location={info.location or 'n/a'} iface={info.interface or 'n/a'}"
            )
    return "metadata unavailable (port not listed)"


def upload_image(
    port: str, raw: bytes, chunk_size: int, timings: bool
) -> None:
    with serial.Serial(port, timeout=2) as ser:
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        if timings:
            click.echo(f"Serial device: {_serial_port_metadata(port)}", err=True)

        exit_interactive_mode(ser)

        # --- begin ---
        send_cmd(ser, "display-image begin")

        # --- chunks ---
        data_size = len(raw)
        offset = 0
        tx_bytes = 0
        t_start = time.monotonic()
        while offset < data_size:
            chunk = raw[offset : offset + chunk_size]
            _, written = send_cmd(ser, f"display-image chunk {chunk.hex()}")
            tx_bytes += written
            offset += len(chunk)
            pct = offset * 100 // data_size
            click.echo(f"  Uploaded {offset}/{data_size} bytes ({pct}%)")
        transfer_elapsed = time.monotonic() - t_start

        # --- end ---
        send_cmd(ser, "display-image end")

        payload_kBs = data_size / transfer_elapsed / 1024 if transfer_elapsed > 0.001 else 0
        wire_kBs = tx_bytes / transfer_elapsed / 1024 if transfer_elapsed > 0.001 else 0
        click.echo(
            f"Done — {data_size} bytes in {transfer_elapsed:.1f}s ({payload_kBs:.0f} kB/s) via {port}."
        )
        if timings:
            click.echo(
                f"Transfer: {tx_bytes} serial bytes in {transfer_elapsed:.3f}s "
                f"({wire_kBs:.0f} kB/s on-wire)",
                err=True,
            )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument("image", metavar="<image>", type=click.Path(exists=True, dir_okay=False))
@click.option("--width", required=True, type=int, help="Target display width in pixels")
@click.option("--height", required=True, type=int, help="Target display height in pixels")
@click.option(
    "--chunk-size",
    "-c",
    default=_MAX_CHUNK_BYTES,
    show_default=True,
    help="Raw bytes per chunk",
)
@click.option("--timings", is_flag=True, help="Print conversion and transfer timing statistics")
def main(
    port: str, image: str, width: int, height: int, chunk_size: int, timings: bool
) -> None:
    """
    Upload an image to prodtest display over serial.

    <serial-port>  e.g. /dev/ttyACM1 or COM3
    <image>        input image path (PNG, JPEG, …)
    """
    chunk_size = min(max(1, chunk_size), _MAX_CHUNK_BYTES)

    t_convert_start = time.monotonic()
    raw = image_to_rgb565_le(Path(image), width, height)
    convert_elapsed = time.monotonic() - t_convert_start
    if timings:
        convert_kBs = len(raw) / convert_elapsed / 1024 if convert_elapsed > 0.001 else 0
        click.echo(
            f"Conversion: {len(raw)} bytes in {convert_elapsed:.3f}s ({convert_kBs:.0f} kB/s)",
            err=True,
        )

    try:
        upload_image(port, raw, chunk_size, timings)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
