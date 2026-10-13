#!/usr/bin/env python3
"""Upload the same image to prodtest displays on multiple serial ports at once.

Converts the image once, then uploads it to every given port in parallel
(one thread per port) so all displays refresh at roughly the same time.

Example:
    python core/tools/display_image_upload_multi.py \\
        /dev/ttyACM0 /dev/ttyACM1 /dev/ttyACM2 /dev/ttyACM3 photo.jpg \\
        --width 240 --height 320 --backlight 180
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import click
import serial

from display_image_converter import image_to_rgb565_le
from display_image_upload import _MAX_CHUNK_BYTES, upload_image


def _upload_one(port: str, raw: bytes, chunk_size: int, timings: bool, backlight: int | None) -> str | None:
    """Run upload_image() for one port, returning an error message on failure (None on success)."""
    try:
        upload_image(port, raw, chunk_size, timings, backlight, label=port)
    except SystemExit:
        return "device reported an error"
    except serial.SerialException as e:
        return f"serial error: {e}"
    except Exception as e:  # noqa: BLE001 - surfaced per-port, not fatal to the whole run
        return f"unexpected error: {e}"
    return None


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("ports", metavar="<serial-port>...", nargs=-1, required=True)
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
@click.option(
    "--backlight",
    type=click.IntRange(0, 255),
    default=None,
    metavar="LEVEL",
    help="Set display backlight level (0-255) on every port before the image is shown",
)
def main(
    ports: tuple[str, ...],
    image: str,
    width: int,
    height: int,
    chunk_size: int,
    timings: bool,
    backlight: int | None,
) -> None:
    """
    Upload the same image (and backlight setting) to one or more prodtest displays
    in parallel, so they show identical contents at the same time.

    <serial-port>... one or more ports, e.g. /dev/ttyACM0 /dev/ttyACM1 ...
                     (Linux: /dev/ttyACM*, macOS: /dev/cu.usbmodem*, Windows: COM*)
    <image>          input image path (PNG, JPEG, …)
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

    click.echo(f"Image: {len(raw)} bytes → {len(ports)} port(s): {', '.join(ports)}")

    try:
        with ThreadPoolExecutor(max_workers=len(ports)) as pool:
            errors = dict(
                zip(
                    ports,
                    pool.map(
                        lambda p: _upload_one(p, raw, chunk_size, timings, backlight), ports
                    ),
                )
            )
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)

    failed = {port: msg for port, msg in errors.items() if msg is not None}
    if failed:
        click.echo("", err=True)
        click.echo(f"{len(failed)}/{len(ports)} port(s) failed:", err=True)
        for port, msg in failed.items():
            click.echo(f"  {port}: {msg}", err=True)
        sys.exit(1)

    click.echo(f"All {len(ports)} port(s) done.")


if __name__ == "__main__":
    main()
