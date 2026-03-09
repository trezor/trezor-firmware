#!/usr/bin/env python3

import shelve

import click

from trezorlib.debuglink import DebugLink
from trezorlib.messages import (
    DebugLinkN4W1Connected,
    DebugLinkN4W1Read,
    DebugLinkN4W1Response,
    DebugLinkN4W1Write,
    Success,
)
from trezorlib.transport.udp import UdpTransport
from trezorlib.transport.webusb import WebUsbTransport


@click.group()
def cli() -> None:
    pass


@cli.command
@click.argument("device_path")
@click.argument("db_file")
def run(device_path: str, db_file: str) -> None:
    """Run basic N4W1 emulator over DebugLink UDP transport."""
    with shelve.open(db_file) as db:
        for k, v in db.items():
            print(f"{k} => {v}")

        if device_path.startswith("webusb"):
            # first matching USB device
            transport = next(
                t.find_debug()
                for t in WebUsbTransport.enumerate()
                if t.get_path().startswith(device_path)
            )
        else:
            # directly open debuglink (without interfering with wirelink UDP port)
            transport = UdpTransport(device_path)

        debug = DebugLink(transport)
        req = debug._call(DebugLinkN4W1Connected())
        while not isinstance(req, Success):
            print(req)
            value = None
            if isinstance(req, DebugLinkN4W1Write):
                if req.key is not None:
                    value = db.pop(req.key, None)
                    db[req.key] = req.value
            elif isinstance(req, DebugLinkN4W1Read):
                if req.key is not None:
                    value = db.get(req.key, None)
            else:
                raise NotImplementedError(req)

            resp = DebugLinkN4W1Response(value=value)
            print(resp)
            req = debug._call(resp)


if __name__ == "__main__":
    cli()
