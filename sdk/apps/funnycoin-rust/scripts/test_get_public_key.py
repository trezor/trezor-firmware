#!/usr/bin/env python3
"""
Test script for Funnycoin GetPublicKey via external app interface.

This script:
1. Serializes a FunnycoinGetPublicKey protobuf message
2. Calls trezorctl extapp run with the serialized data
3. Deserializes the FunnycoinPublicKey response
"""

import sys
import subprocess
import io
from pathlib import Path

# Add trezorlib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "python" / "src"))

from trezorlib import messages, protobuf

def main():
    # Create the GetPublicKey request
    request = messages.FunnycoinGetPublicKey(
        address_n=[0x8000002c, 0x80000000, 0x80000000],  # m/44'/0'/0'
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
    app_path = Path(__file__).parent.parent / "target" / "debug" / "libfunnycoin_rust.so"
    print(f"\nLoading app from: {app_path}")

    load_result = subprocess.run(
        ["trezorctl", "extapp", "load", str(app_path)],
        capture_output=True,
        text=True,
    )

    if load_result.returncode != 0:
        print(f"Error loading app: {load_result.stderr}")
        sys.exit(1)

    # Extract hash from output like "Loaded app hash: abc123..."
    import re
    load_match = re.search(r"Loaded app hash:\s*([0-9A-Fa-f]+)", load_result.stdout)
    if not load_match:
        print(f"Could not extract app hash from load output:\n{load_result.stdout}")
        sys.exit(1)

    app_hash = load_match.group(1)
    fn_id = 0  # GetPublicKey function ID
    print(f"Loaded app hash: {app_hash}")

    print(f"\nCalling trezorctl extapp run...")
    print(f"  Command: trezorctl extapp run {app_hash} {fn_id} {request_data.hex()}")

    result = subprocess.run(
        ["trezorctl", "extapp", "run", app_hash, str(fn_id), request_data.hex()],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Parse the response: extapp CLI prints human-friendly lines like
        #   Result: ...\nData: <hex>
        import re
        stdout = result.stdout.strip()
        print(f"\nRaw trezorctl stdout:\n{stdout}")
        m = re.search(r"^Data:\s*([0-9A-Fa-f]+)\s*$", stdout, re.MULTILINE)
        if not m:
            print("Could not find hex payload in trezorctl output. Expected a 'Data: <hex>' line.")
            sys.exit(1)
        response_hex = m.group(1)
        response_data = bytes.fromhex(response_hex)
        response_buf = io.BytesIO(response_data)
        response = protobuf.load_message(response_buf, messages.FunnycoinPublicKey)
        print(f"\nResponse (parsed): {response}")
        print(f"  xpub: {response.xpub}")
        if response.public_key:
            print(f"  public_key: {response.public_key.hex()}")
    else:
        print(f"Error: {result.stderr}")

if __name__ == "__main__":
    main()
