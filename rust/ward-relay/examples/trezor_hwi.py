#!/usr/bin/env python3
"""Development HWI: forward WARD messages on one existing emulator session."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trezorlib import messages, protobuf
from trezorlib.client import Session
from trezorlib.debuglink import TrezorTestContext
from trezorlib.testing.device_handler import BackgroundDeviceHandler
from trezorlib.transport import get_transport


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delays",
        action="store_true",
        default=os.environ.get("WARD_DELAYS") == "1",
        help="Pause one second at each WARD forwarding step",
    )
    device_path = os.environ.get("TREZOR_PATH")
    if device_path is None and os.environ.get("TREZOR_UDP_PORT"):
        device_path = f"udp:127.0.0.1:{os.environ['TREZOR_UDP_PORT']}"
    parser.add_argument(
        "--path",
        default=device_path,
        required=device_path is None,
        help="Device path; defaults to TREZOR_PATH or TREZOR_UDP_PORT",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get(
            "WARDD_URL", f"ws://127.0.0.1:{os.environ.get('WARDD_PORT', '21329')}"
        ),
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=Path(
            os.environ.get("WARD_TOKEN_FILE", str(Path.home() / ".trezor-ward/token"))
        ),
    )
    parser.add_argument("--address", default="bc1qwarddemo")
    parser.add_argument(
        "--label", help="Also confirm and write this label on the debug emulator"
    )
    parser.add_argument(
        "--jade-host", action="store_true", help="Import through jadepy.ward"
    )
    args = parser.parse_args()

    def handoff(hop: str, name: str) -> None:
        if args.delays:
            print(
                json.dumps(
                    {
                        "time": datetime.now(timezone.utc).isoformat(
                            timespec="milliseconds"
                        ),
                        "service": "HWI",
                        "event": "forward.delay",
                        "hop": hop,
                        "name": name,
                        "delayMs": 1000,
                    }
                ),
                flush=True,
            )
            time.sleep(1)

    if args.jade_host:
        from jadepy.ward import WardAdapter
    else:
        from ward_relay import WardAdapter

    handoff("HWI -> wardd", "hello")
    with (
        TrezorTestContext(get_transport(args.path)) as hwi,
        WardAdapter(token=args.token_file.read_text().strip(), url=args.url) as adapter,
    ):
        session = hwi.get_session()

        def answer_proof(request: messages.WARDProofRequest) -> messages.WARDProofAck:
            handoff("HWI -> adapter", "WARDProofRequest")
            ack = adapter.answer_ward_request(
                type(request).__name__, protobuf.to_dict(request)
            )
            handoff("HWI -> Trezor", "WARDProofAck")
            return protobuf.dict_to_proto(messages.WARDProofAck, ack["message"])

        def call(
            active: Session, method: str, params: dict[str, Any]
        ) -> dict[str, Any]:
            def device_call(
                name: str, body: dict[str, Any]
            ) -> tuple[str, dict[str, Any]]:
                request = protobuf.dict_to_proto(getattr(messages, name), body)
                handoff("HWI -> Trezor", name)
                response = active.call(request)
                handoff("HWI -> adapter", type(response).__name__)
                return type(response).__name__, protobuf.to_dict(response)

            handoff("HWI -> adapter", method)
            result = adapter.call(method, params, device_call)
            handoff("adapter -> HWI", method)
            return result

        previous = session.client.app.ward_proof_callback
        session.client.app.ward_proof_callback = answer_proof
        try:
            print("sync:", json.dumps(call(session, "sync", {})), flush=True)
            params = {
                "appId": "bitcoin",
                "address": args.address,
                "networkSymbol": "btc",
            }
            if args.label is not None:
                with BackgroundDeviceHandler(hwi) as worker:
                    worker.run_with_provided_session(
                        session,
                        lambda active: call(
                            active,
                            "update",
                            {**params, "metadata": {"label": args.label}},
                        ),
                    )
                    debug = worker.debuglink()
                    deadline = time.monotonic() + (180 if args.delays else 30)
                    while "Homescreen" in debug.read_layout(wait=False).json_str:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("No confirmation appeared")
                        time.sleep(0.1)
                    debug.press_yes()
                    print("write:", json.dumps(worker.result()), flush=True)
            print("lookup:", json.dumps(call(session, "lookup", params)), flush=True)
        finally:
            session.client.app.ward_proof_callback = previous


if __name__ == "__main__":
    main()
