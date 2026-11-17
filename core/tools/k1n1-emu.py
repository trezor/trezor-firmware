#!/usr/bin/env python3

"""Emulate an K1N1 card for the emulator over DebugLink."""

import json
import logging
import sys
from pathlib import Path

import click

from trezorlib.debuglink import DebugLink
from trezorlib.transport import Transport
from trezorlib.transport.udp import UdpTransport
from trezorlib.transport.webusb import WebUsbTransport

# the card emulation lives in the test suite, which is not installed
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests import k1n1  # noqa: E402  # type: ignore ["k1n1" is unknown import symbol]


def load_card(path: Path) -> k1n1.K1N1Tag:
    if not path.exists():
        card = k1n1.K1N1Tag()
        save_card(path, card)
        click.echo(f"Created a new card in {path}")
        return card
    return k1n1.K1N1Tag.from_dict(json.loads(path.read_text()))


def save_card(path: Path, card: k1n1.K1N1Tag) -> None:
    path.write_text(json.dumps(card.to_dict(), indent=2) + "\n")


def open_transport(device_path: str) -> Transport:
    if device_path.startswith("webusb"):
        # first matching USB device
        return next(
            t.find_debug()
            for t in WebUsbTransport.enumerate()
            if t.get_path().startswith(device_path)
        )
    # directly open debuglink (without interfering with wirelink UDP port)
    return UdpTransport(device_path)


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("device_path")
@click.argument("card_file", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "-v", "--verbose", is_flag=True, help="Log APDUs exchanged with the card."
)
def run(device_path: str, card_file: Path, verbose: bool) -> None:
    """Tap the card stored in CARD_FILE to the device at DEVICE_PATH.

    The card stays in the field until the device ends the NFC session. CARD_FILE
    is created with a fresh card if it doesn't exist, and updated afterwards.
    """
    logging.basicConfig(format="%(message)s")
    k1n1.LOG.setLevel(logging.DEBUG if verbose else logging.INFO)

    card = load_card(card_file)
    click.echo(f"Card UID: {card.uid.hex()}")
    debug = DebugLink(open_transport(device_path))
    try:
        k1n1.tap_over_debuglink(debug, card)
    finally:
        save_card(card_file, card)


if __name__ == "__main__":
    cli()
