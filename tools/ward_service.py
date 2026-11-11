#!/usr/bin/env python3
"""Serve a device's dedicated WARD interface through the existing wardd daemon."""

import argparse
from pathlib import Path

from trezorlib.transport import get_transport
from trezorlib.ward_relay import WarddClient
from trezorlib.ward_service import WardService, ward_transport


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        required=True,
        help="wallet USB/UDP path; service is discovered separately",
    )
    parser.add_argument("--url", default="ws://127.0.0.1:21329")
    parser.add_argument("--token-file", type=Path, required=True)
    args = parser.parse_args()
    wire = get_transport(args.path)
    with WarddClient(
        token=args.token_file.read_text().strip(), url=args.url
    ) as backend:
        service = WardService(ward_transport(wire), backend)
        service.open()
        print("WARD service bound (64-byte private wire buffer)", flush=True)
        try:
            while True:
                service.serve_one()
        except KeyboardInterrupt:
            pass
        finally:
            service.close()


if __name__ == "__main__":
    main()
