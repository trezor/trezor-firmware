#!/usr/bin/env python3
"""Smoke test of a device's debuglink over any transport.

Opens the transport, derives the debuglink from it, and runs a few requests
with timings: a DebugLinkGetState round trip, a layout read (a reply of
several reports, so it exercises the device-to-host flow control), and a
burst of round trips for a throughput figure. Nothing on the device changes.

Examples:
    debuglink_check.py ble:FB:18:A1:65:60:5F     # debuglink over BLE
    debuglink_check.py                            # TREZOR_PATH, else first device
    debuglink_check.py udp:127.0.0.1:21324        # emulator
    debuglink_check.py --rounds 50 ble:FB:18:A1:65:60:5F
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from types import TracebackType

from trezorlib import messages
from trezorlib.debuglink import DebugLink
from trezorlib.transport import TransportException, get_transport


class Step:
    """Prints a label, then the elapsed time or the error of the block."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.start = 0.0

    def __enter__(self) -> "Step":
        print(f"{self.label:<34}", end="", flush=True)
        self.start = time.monotonic()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        elapsed = time.monotonic() - self.start
        if exc is None:
            print(f"ok   {elapsed * 1000:7.0f} ms", flush=True)
        else:
            text = str(exc) or type(exc).__name__
            print(f"FAIL {elapsed * 1000:7.0f} ms  {text}", flush=True)
        return False


def step(label: str) -> Step:
    return Step(label)


def list_ble_neighbourhood() -> None:
    """After a failed BLE lookup: what a scan sees, to tell "not advertising"
    from "advertising but not recognised"."""
    import asyncio

    from bleak import BleakScanner

    from trezorlib.transport.ble import (
        TREZOR_DEBUG_SERVICE_UUID,
        TREZOR_SERVICE_UUID,
    )

    async def scan() -> None:
        found = await BleakScanner.discover(timeout=5.0, return_adv=True)
        print("BLE devices seen in 5 s:", file=sys.stderr)
        pairing: list[str] = []
        for dev, adv in found.values():
            if not dev.name and TREZOR_SERVICE_UUID not in adv.service_uuids:
                continue
            tags = []
            if TREZOR_SERVICE_UUID in adv.service_uuids:
                tags.append("wire")
            if TREZOR_DEBUG_SERVICE_UUID in adv.service_uuids:
                tags.append("debuglink")
            mdata = adv.manufacturer_data.get(0x0F29)
            if mdata:
                tags.append(f"trezor flags=0x{mdata[0]:02x}")
                if mdata[0] & 0x01:
                    tags.append("PAIRING MODE")
                    pairing.append(dev.name or dev.address)
            print(
                f"  {dev.address}  {dev.name or '-':<28} rssi={adv.rssi:4}  "
                + ", ".join(tags),
                file=sys.stderr,
            )

        for name in pairing:
            print(
                f"{name!r} is in pairing mode under a private address, so this "
                "host holds no bond for it. Pair first, e.g. "
                f'core/tools/console.py --ble "{name}", then retry with the '
                "identity address the bonded host sees.",
                file=sys.stderr,
            )

    asyncio.run(scan())


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "path",
        nargs="?",
        default=os.environ.get("TREZOR_PATH"),
        help="transport path (ble:ADDR, udp:HOST:PORT, webusb:...); "
        "default TREZOR_PATH, else the first device found",
    )
    parser.add_argument(
        "--rounds", type=int, default=20, help="round trips for the throughput figure"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="seconds to wait for each reply before giving up (default 10)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    try:
        with step(f"transport {args.path or '(auto)'}"):
            transport = get_transport(args.path, prefix_search=True)
            print(f"[{transport.get_path()}] ", end="")

        with step("find_debug"):
            debug_transport = transport.find_debug()
            print(f"[{debug_transport.get_path()}] ", end="")

        with step("open debuglink"):
            debug = DebugLink(debug_transport, auto_interact=False)

        with step("DebugLinkGetState"):
            # the public state() waits forever; a hang must fail, not sit
            state = debug._call(
                messages.DebugLinkGetState(),
                timeout=args.timeout,
                expect=messages.DebugLinkState,
            )
        print(f"    layout_lines: {len(state.tokens or [])} tokens")

        with step("read_layout"):
            layout = debug.read_layout()
        screen = layout.visible_screen().strip()
        print("    screen: " + (screen.splitlines()[0] if screen else "(empty)"))

        with step(f"{args.rounds} x DebugLinkGetState") as s:
            for _ in range(args.rounds):
                debug._call(messages.DebugLinkGetState(), timeout=args.timeout)
        per_round = (time.monotonic() - s.start) / max(args.rounds, 1)
        print(f"    {per_round * 1000:.0f} ms per round trip")

        with step("close"):
            debug.close()
    except TransportException as e:
        print(f"\ntransport error: {e}", file=sys.stderr)
        if args.path and args.path.startswith("ble"):
            list_ble_neighbourhood()
        return 1
    except Exception as e:
        print(f"\nfailed: {str(e) or type(e).__name__}", file=sys.stderr)
        if args.verbose:
            raise
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
