#!/usr/bin/env python3
"""
Test script for Funnycoin GetPublicKey via external app interface.

This script:
1. Serializes a FunnycoinGetPublicKey protobuf message
2. Calls trezorctl extapp run with the serialized data
3. Deserializes the FunnycoinPublicKey response
"""

import io
from pathlib import Path

from trezorlib.client import get_default_client
from trezorlib import messages, protobuf, extapp


def main():
    client = get_default_client()

    # Create the GetPublicKey request
    request = messages.FunnycoinGetPublicKey(
        address_n=[0x8000002C, 0x80000000, 0x80000000],  # m/44'/0'/0'
        coin_name="Funnycoin",
        show_display=False,
    )

    # Serialize to bytes
    buf = io.BytesIO()
    protobuf.dump_message(buf, request)
    request_data = buf.getvalue()

    print(f"Request: {request}")
    print(f"Serialized ({len(request_data)} bytes): {request_data.hex()}")

    # Load the app and get its hash
    app_path = Path(__file__).parent.parent / "target" / "debug" / "funnycoin_rust"
    print(f"\nLoading app from: {app_path}")

    session = client.get_seedless_session()
    instance_id = extapp.load(session, app_path.read_bytes())

    request = messages.ExtAppMessage(
        instance_id=instance_id,
        message_id=0,
        data=request_data,
    )
    resp = session.call(request, expect=messages.ExtAppResponse)

    buf = io.BytesIO(resp.data)
    response = protobuf.load_message(buf, messages.FunnycoinPublicKey)
    print(protobuf.format_message(response))


if __name__ == "__main__":
    main()
