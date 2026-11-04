#!/usr/bin/env python3

import dbm

import click

from trezorlib.debuglink import DebugLink
from trezorlib.messages import (
    DebugLinkK1N1Connected,
    DebugLinkK1N1Read,
    DebugLinkK1N1Response,
    DebugLinkK1N1Write,
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
    """Run basic K1N1 emulator over DebugLink transport."""
    with dbm.open(db_file, "c") as db:
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
        req = debug._call(DebugLinkK1N1Connected())
        while not isinstance(req, Success):
            print(req)
            value = None
            if isinstance(req, DebugLinkK1N1Write):
                if req.key is not None:
                    # fetch the existing item
                    value = db.get(req.key, None)
                    # insert a new one, or delete (if the new value is None)
                    if req.value is not None:
                        db[req.key] = req.value
                    elif value is not None:
                        del db[req.key]
            elif isinstance(req, DebugLinkK1N1Read):
                if req.key is not None:
                    value = db.get(req.key, None)
            else:
                raise NotImplementedError(req)

            resp = DebugLinkK1N1Response(value=value)
            print(resp)
            req = debug._call(resp)


if __name__ == "__main__":
    cli()
