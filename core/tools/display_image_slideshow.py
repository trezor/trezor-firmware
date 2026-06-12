#!/usr/bin/env python3
"""Send a directory of images to prodtest display as a slideshow.

Images are sent one by one via `display-image begin/chunk/end`,
with a configurable pause between each.  The serial port is opened once
and kept open for the whole run.

Example:
    python core/tools/display_image_slideshow.py /dev/ttyACM1 images/ \\
        --width 240 --height 320

    python core/tools/display_image_slideshow.py /dev/ttyACM1 images/ \\
        --width 240 --height 320 --delay 5 --loop
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import click
import serial

from display_image_converter import image_to_rgb565_le

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}

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


def send_cmd(
    ser: serial.Serial, cmd: str, expect_ok: bool = True, log: bool = True
) -> tuple[str, int]:
    """Send a line, read response, and abort on CLI_ERROR."""
    written = ser.write((cmd + "\r\n").encode())
    time.sleep(0.05)
    resp = ser.readline().decode(errors="ignore").strip()
    while resp.startswith("#") or len(resp) == 0:
        resp = ser.readline().decode(errors="ignore").strip()
    if log:
        click.echo(f"> {_format_cmd_for_log(cmd)}")
        click.echo(f"< {resp}")
    if expect_ok and not resp.startswith("OK"):
        click.echo(f"Error from device, aborting.", err=True)
        sys.exit(1)
    return resp, written


def upload_image(ser: serial.Serial, raw: bytes, chunk_size: int) -> float:
    send_cmd(ser, "display-image begin")

    data_size = len(raw)
    offset = 0
    t_start = time.monotonic()
    while offset < data_size:
        chunk = raw[offset : offset + chunk_size]
        send_cmd(ser, f"display-image chunk {chunk.hex()}", log=False)
        offset += len(chunk)
        pct = offset * 100 // data_size
        click.echo(f"  {offset}/{data_size} bytes ({pct}%)")
    elapsed = time.monotonic() - t_start

    send_cmd(ser, "display-image end")
    return elapsed


def collect_images(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument(
    "directory",
    metavar="<image-directory>",
    type=click.Path(exists=True, file_okay=False),
)
@click.option("--width", required=True, type=int, help="Target display width in pixels")
@click.option("--height", required=True, type=int, help="Target display height in pixels")
@click.option(
    "--delay",
    default=10.0,
    show_default=True,
    help="Seconds to wait between images",
)
@click.option("--loop", is_flag=True, help="Loop through the directory indefinitely")
@click.option(
    "--chunk-size",
    "-c",
    default=_MAX_CHUNK_BYTES,
    show_default=True,
    help="Raw bytes per chunk",
)
@click.option(
    "--backlight",
    type=int,
    default=None,
    metavar="LEVEL",
    help="Set display backlight level (0-255) before the slideshow starts",
)
def main(
    port: str,
    directory: str,
    width: int,
    height: int,
    delay: float,
    loop: bool,
    chunk_size: int,
    backlight: int | None,
) -> None:
    """
    Send a directory of images to prodtest display as a slideshow.

    <serial-port>      e.g. /dev/ttyACM1 or COM3
    <image-directory>  directory containing image files
    """
    images = collect_images(Path(directory))
    if not images:
        click.echo(f"No images found in {directory}", err=True)
        sys.exit(1)

    chunk_size = min(max(1, chunk_size), _MAX_CHUNK_BYTES)

    click.echo(f"Found {len(images)} image(s) in {directory}")

    try:
        with serial.Serial(port, timeout=2) as ser:
            time.sleep(0.1)
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            exit_interactive_mode(ser)

            if backlight is not None:
                send_cmd(ser, f"display-set-backlight {backlight}")

            iteration = 0
            while True:
                for idx, path in enumerate(images):
                    click.echo(f"[{idx + 1}/{len(images)}] {path.name}")

                    try:
                        raw = image_to_rgb565_le(path, width, height)
                    except Exception as exc:
                        click.echo(f"  Skipped ({exc})", err=True)
                        continue

                    elapsed = upload_image(ser, raw, chunk_size)
                    kBs = len(raw) / elapsed / 1024 if elapsed > 0.001 else 0
                    click.echo(f"  {len(raw)} bytes in {elapsed:.1f}s ({kBs:.0f} kB/s)")

                    is_last = idx == len(images) - 1
                    if loop or not is_last:
                        click.echo(f"  Waiting {delay:.1f}s...")
                        time.sleep(delay)

                iteration += 1
                if not loop:
                    break
                click.echo(f"--- loop {iteration} complete, restarting ---")

    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
