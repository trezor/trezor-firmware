#!/usr/bin/env python3
"""Development HWI: forward WARD messages on one existing emulator session."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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
        "--long",
        action="store_true",
        help="Write ten distinct entries and verify each lookup",
    )
    parser.add_argument(
        "--extra_long",
        "--extra-long",
        action="store_true",
        help="Cover every bounded state/operation combination through depth 10",
    )
    parser.add_argument(
        "--label", help="Also confirm and write this label on the debug emulator"
    )
    parser.add_argument(
        "--jade-host", action="store_true", help="Import through jadepy.ward"
    )
    parser.add_argument(
        "--adversarial",
        action="store_true",
        help="Run protocol attack/rejection tests on this emulator",
    )
    args = parser.parse_args()
    if args.adversarial:
        if args.long or args.extra_long:
            parser.error("Run --adversarial separately from --long/--extra_long")
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[3] / "tools/ward_adversarial.py"),
                "--path",
                args.path,
            ],
            check=True,
        )
        return

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
            if args.extra_long:
                from trezorlib._internal.ward_stress import run_extra_long

                def confirmed(operation, expected_label=None):
                    with BackgroundDeviceHandler(hwi) as worker:
                        worker.run_with_provided_session(session, lambda _: operation())
                        debug = worker.debuglink()
                        deadline = time.monotonic() + (180 if args.delays else 30)
                        layout = debug.read_layout(wait=False).json_str
                        while "Homescreen" in layout:
                            if time.monotonic() >= deadline:
                                raise TimeoutError("No WARD confirmation appeared")
                            time.sleep(0.05)
                            layout = debug.read_layout(wait=False).json_str
                        if expected_label is not None and expected_label not in layout:
                            raise AssertionError(
                                f"Device did not display {expected_label!r}"
                            )
                        debug.press_yes()
                        return worker.result()

                def display(params, expected_label):
                    result = confirmed(
                        lambda: session.call(
                            messages.DisplayAddress(
                                address=params["address"], app_id=params["appId"]
                            )
                        ),
                        expected_label,
                    )
                    if not isinstance(result, messages.Success):
                        raise AssertionError(f"DisplayAddress failed: {result}")

                def verify_lookup(params):
                    reply = session.call(
                        messages.WARDLookup(
                            address=params["address"].encode(),
                            app_id=params["appId"],
                            key_type="address",
                            proof=[],
                        )
                    )
                    if not isinstance(reply, messages.WARDLookupAck):
                        raise AssertionError(f"WARDLookup failed: {reply}")
                    return {
                        "valid": reply.valid,
                        "isMember": reply.membership,
                        "counter": reply.counter,
                        "wardId": bytes(reply.ward_id).hex()
                        if reply.ward_id is not None
                        else None,
                    }

                run_extra_long(
                    lambda method, params: call(session, method, params),
                    confirmed,
                    display,
                    lambda event: print(
                        json.dumps(
                            {
                                "time": datetime.now(timezone.utc).isoformat(
                                    timespec="milliseconds"
                                ),
                                "service": "HWI",
                                **event,
                            }
                        ),
                        flush=True,
                    ),
                    args.address,
                    verify_lookup=verify_lookup,
                )
                return
            print("sync:", json.dumps(call(session, "sync", {})), flush=True)
            count = 10 if args.long else 1
            label = (
                args.label
                if args.label is not None
                else ("WARD demo" if args.long else None)
            )
            entries = [
                {
                    "appId": "bitcoin",
                    "address": args.address
                    if index == 0
                    else f"{args.address}-{index + 1:02d}",
                    "networkSymbol": "btc",
                }
                for index in range(count)
            ]
            for index, params in enumerate(entries):
                if label is None:
                    continue
                entry_label = label if not args.long else f"{label} {index + 1:02d}"
                with BackgroundDeviceHandler(hwi) as worker:
                    worker.run_with_provided_session(
                        session,
                        lambda active: call(
                            active,
                            "update",
                            {**params, "metadata": {"label": entry_label}},
                        ),
                    )
                    debug = worker.debuglink()
                    deadline = time.monotonic() + (180 if args.delays else 30)
                    while "Homescreen" in debug.read_layout(wait=False).json_str:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("No confirmation appeared")
                        time.sleep(0.1)
                    debug.press_yes()
                    result = worker.result()
                    if result.get("conflict") or result.get("localCacheError"):
                        raise RuntimeError(f"WARD write failed: {result}")
                    print(f"write {index + 1}/{count}:", json.dumps(result), flush=True)
            for index, params in enumerate(entries):
                result = call(session, "lookup", params)
                if label is not None:
                    expected_label = (
                        label if not args.long else f"{label} {index + 1:02d}"
                    )
                    if not (result.get("valid") and result.get("isMember")):
                        raise RuntimeError(
                            f"WARD lookup failed for entry {index + 1}: {result}"
                        )
                    if args.long:
                        with BackgroundDeviceHandler(hwi) as worker:
                            worker.run_with_provided_session(
                                session,
                                lambda active: active.call(
                                    messages.DisplayAddress(
                                        address=params["address"], app_id="bitcoin"
                                    )
                                ),
                            )
                            debug = worker.debuglink()
                            deadline = time.monotonic() + (180 if args.delays else 30)
                            layout = debug.read_layout(wait=False).json_str
                            while "Homescreen" in layout:
                                if time.monotonic() >= deadline:
                                    raise TimeoutError(
                                        "No authenticated label display appeared"
                                    )
                                time.sleep(0.1)
                                layout = debug.read_layout(wait=False).json_str
                            if expected_label not in layout:
                                raise RuntimeError(
                                    f"Trezor did not show the expected label for entry {index + 1}"
                                )
                            debug.press_yes()
                            worker.result()
                print(f"lookup {index + 1}/{count}:", json.dumps(result), flush=True)
        finally:
            session.client.app.ward_proof_callback = previous


if __name__ == "__main__":
    main()
