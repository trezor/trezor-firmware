#!/usr/bin/env python3
"""
Test script for Ethereum GetPublicKey via external app interface.

This script:
1. Serializes an EthereumGetPublicKey protobuf message
2. Calls trezorctl extapp run with the serialized data
3. Deserializes the EthereumPublicKey response
"""

import io
from pathlib import Path

from trezorlib.client import get_default_client
from trezorlib import messages, protobuf, extapp

HARDENED = 0x80000000


def parse_derivation_path(path: str) -> list[int]:
    path = path.strip()
    if not path:
        raise ValueError("empty derivation path")

    parts = path.split("/")
    if parts and parts[0].lower() == "m":
        parts = parts[1:]

    out: list[int] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        hardened = part.endswith("'")
        if hardened:
            part = part[:-1]
        if not part.isdigit():
            raise ValueError(f"invalid path component: {part!r}")
        idx = int(part, 10)
        if idx < 0 or idx >= HARDENED:
            raise ValueError(f"invalid index (must be < 2^31): {idx}")
        out.append(idx | (HARDENED if hardened else 0))
    return out


def format_address_n_hex(address_n: list[int]) -> str:
    return "[" + ", ".join(f"0x{x:08x}" for x in address_n) + "]"


def main():
    client = get_default_client("ethereum")

    derivation_path = "m/44'/60'/0'"
    print(f"Derivation path: {derivation_path}")

    address_n = parse_derivation_path(derivation_path)
    print(f"Address_n: {format_address_n_hex(address_n)}")

    # Create the GetPublicKey request
    request = messages.EthereumGetPublicKey(
        address_n=address_n,
        show_display=True,
    )

    # Serialize to bytes
    buf = io.BytesIO()
    protobuf.dump_message(buf, request)
    request_data = buf.getvalue()

    print(f"Request: {request}")
    print(f"Serialized ({len(request_data)} bytes): {request_data.hex()}")

    # Load the app and get its hash
    app_path = Path(__file__).parent.parent / "target" / "debug" / "ethereum_rust"
    # app_path = Path(__file__).parent.parent / "target" / "release" / "ethereum_rust"
    #app_path = Path(__file__).parent.parent / "target" / "thumbv7em-none-eabihf" / "debug" / "ethereum_rust.min"
    # app_path = Path(__file__).parent.parent / "target" / "thumbv7em-none-eabihf" / "release" / "ethereum_rust.min"
    print(f"\nLoading app from: {app_path}")

    session = client.get_session()
    instance_id = extapp.load(session, app_path.read_bytes())

    request = messages.ExtAppMessage(
        instance_id=instance_id,
        message_id=0,
        data=request_data,
    )
    resp = session.call(request, expect=messages.ExtAppResponse)

    buf = io.BytesIO(resp.data)
    response = protobuf.load_message(buf, messages.EthereumPublicKey)
    print(protobuf.format_message(response))


if __name__ == "__main__":
    main()
