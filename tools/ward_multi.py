#!/usr/bin/env python3
"""Exercise same-seed devices through the shared Rust adapter and a running stack."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ward_stack import debug_request, load_config
from trezorlib import exceptions, messages, ward
from trezorlib.debuglink import TrezorTestContext
from trezorlib.testing.device_handler import BackgroundDeviceHandler
from trezorlib.transport import get_transport


def run(config: dict[str, Any]) -> list[str]:
    from ward_relay import WardAdapter

    from tools.ward_manager import DEBUG_SEED, WardManager

    passed: list[str] = []

    def checked(name: str) -> None:
        passed.append(name)
        print(
            json.dumps({"time": time.time(), "test": name, "result": "passed"}),
            flush=True,
        )

    with ExitStack() as stack:
        devices = []
        for index in range(config["devices"]):
            context = stack.enter_context(
                TrezorTestContext(
                    get_transport(
                        f"udp:127.0.0.1:{config['emulator_port'] + 8 * index}"
                    )
                )
            )
            session = context.get_session()
            adapter = stack.enter_context(
                WardAdapter(
                    token=Path(config["environment"]["WARD_TOKEN_FILE"])
                    .read_text()
                    .strip(),
                    url=config["environment"]["WARDD_URL"],
                )
            )
            adapter.set_logging(False)
            forwarding = stack.enter_context(adapter.session(session))
            devices.append((context, session, forwarding))

        def call(
            index: int, method: str, params: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return devices[index][2].call(
                method, {**(params or {}), "debugDeviceId": f"device-{index + 1}"}
            )

        def confirmed(
            index: int,
            operation: Callable[[], Any],
            expected_text: str | None = None,
            approve: bool = True,
        ) -> Any:
            context, session, _ = devices[index]
            with BackgroundDeviceHandler(context) as worker:
                worker.run_with_provided_session(session, lambda _: operation())
                debug = worker.debuglink()
                deadline = time.monotonic() + config.get("timeout", 90)
                while "Homescreen" in debug.read_layout(wait=False).json_str:
                    if time.monotonic() > deadline:
                        raise TimeoutError("No device confirmation appeared")
                    time.sleep(0.05)
                if expected_text is not None:
                    assert expected_text in debug.read_layout(wait=False).json_str
                time.sleep(config.get("confirm_delay", 2.0))
                if approve:
                    debug.press_yes()
                else:
                    debug.press_no()
                return worker.result()

        def update(
            index: int, address: str, label: str, deleting: bool = False
        ) -> dict[str, Any]:
            return confirmed(
                index,
                lambda: call(
                    index,
                    "update",
                    {
                        "appId": "bitcoin",
                        "address": address,
                        "networkSymbol": "btc",
                        "metadata": {"label": label},
                        "delete": deleting,
                    },
                ),
            )

        def pending(index: int) -> list[int]:
            return list(
                devices[index][1]
                .call(
                    messages.WARDListPendingEdits(),
                    expect=messages.WARDListPendingEditsAck,
                )
                .pending_ids
            )

        def anchor(index: int):
            return devices[index][1].call(
                messages.WARDSync(), expect=messages.WARDSyncAck
            )

        if config.get("scenario") == "recovery":
            from tools.ward_recovery import run_recovery

            update(1, "ward-recovery-retained", "entry that must survive recovery")
            run_recovery(
                config=config,
                devices=devices,
                call=call,
                update=update,
                anchor=anchor,
                pending=pending,
                confirmed=confirmed,
                checked=checked,
            )
            return passed
        if config.get("scenario") == "races":
            from tools.ward_races import run_races

            run_races(
                config=config,
                devices=devices,
                call=call,
                update=update,
                anchor=anchor,
                pending=pending,
                confirmed=confirmed,
                checked=checked,
            )
            return passed

        heads = [call(i, "sync") for i in range(len(devices))]
        assert len({head["wardId"] for head in heads}) == 1, (
            "devices do not share a seed/wallet"
        )
        checked("same-seed-wallet")
        first = update(0, "ward-shared-first", "from first device")
        second = call(1, "sync")
        assert (second["counter"], second["root"]) == (first["counter"], first["root"])
        assert call(
            1,
            "lookup",
            {
                "appId": "bitcoin",
                "address": "ward-shared-first",
                "networkSymbol": "btc",
            },
        )["isMember"]
        checked("cross-device-synchronization")

        assert debug_request(config, "PAUSE", "device-1")["paused"]
        before = anchor(0)
        queued = update(0, "ward-offline-first", "queued while WM unavailable")
        assert queued.get("queued") and queued["pendingId"] in pending(0)
        assert update(0, "ward-offline-second", "second queued edit").get("queued")
        assert update(0, "ward-shared-first", "", deleting=True).get("queued")
        assert len(pending(0)) == 3
        assert anchor(0).counter == before.counter
        active = update(1, "ward-online-second", "online device still works")
        assert active["counter"] > before.counter and not active.get("queued")
        checked("one-device-offline-queues-without-advancing-anchor")

        # CONTINUE restores access; the next sync must drain the device's durable queue.
        assert not debug_request(config, "CONTINUE", "device-1")["paused"]
        drained = call(0, "sync")
        assert not pending(0) and drained["counter"] == active["counter"] + 3
        other = call(1, "sync")
        assert (other["counter"], other["root"]) == (
            drained["counter"],
            drained["root"],
        )
        for index in (0, 1):
            for address in (
                "ward-offline-second",
                "ward-offline-first",
                "ward-online-second",
            ):
                verdict = call(
                    index,
                    "lookup",
                    {"appId": "bitcoin", "address": address, "networkSymbol": "btc"},
                )
                assert verdict["valid"] and verdict["isMember"]
        assert not call(
            1,
            "lookup",
            {
                "appId": "bitcoin",
                "address": "ward-shared-first",
                "networkSymbol": "btc",
            },
        )["isMember"]
        checked("reconnect-integrates-queue-and-preserves-online-changes")

        for index in (0, 1):
            debug_request(config, "PAUSE", f"device-{index + 1}")
            result = update(index, "ward-collision", f"same-entry intent {index}")
            assert result.get("queued") and pending(index)
        debug_request(config, "CONTINUE", "device-2")
        winner = call(1, "sync")
        debug_request(config, "CONTINUE", "device-1")
        merged = call(0, "sync")
        assert merged["counter"] == winner["counter"] + 1
        assert not pending(0) and not pending(1)
        final = call(1, "sync")
        assert (merged["counter"], merged["root"]) == (final["counter"], final["root"])
        assert call(
            1,
            "lookup",
            {"appId": "bitcoin", "address": "ward-collision", "networkSymbol": "btc"},
        )["isMember"]
        confirmed(
            1,
            lambda: devices[1][1].call(
                messages.DisplayAddress(address="ward-collision", app_id="bitcoin")
            ),
            "same-entry intent 0",
        )
        checked("same-entry-collision-serializes-both-authorized-intents")

        for index in (0, 1):
            session = devices[index][1]
            trusted = anchor(index)
            # A restored WM backup can still sign fresh challenges, but cannot lower the device floor.
            stale = WardManager(":memory:", DEBUG_SEED)
            try:
                attested = stale.attest(
                    {"wardId": trusted.ward_id.hex(), "nonce": trusted.nonce.hex()}
                )
            finally:
                stale.close()
            try:
                ward.ingest_attestation(
                    session,
                    0,
                    None,
                    bytes.fromhex(attested["signature"]),
                    timestamp=attested["timestamp"],
                    head_nonce=bytes.fromhex(attested["headNonce"]),
                )
            except exceptions.TrezorFailure as error:
                assert "older than counter_loc" in str(error), str(error)
            else:
                raise AssertionError("device accepted a validly signed rollback")
            assert anchor(index).counter == trusted.counter
            # Reusing the signature with a new device challenge must fail independently of the floor.
            try:
                ward.ingest_attestation(
                    session,
                    0,
                    None,
                    bytes.fromhex(attested["signature"]),
                    timestamp=attested["timestamp"],
                    head_nonce=bytes.fromhex(attested["headNonce"]),
                )
            except exceptions.TrezorFailure as error:
                assert "attestation verification failed" in str(error), str(error)
            else:
                raise AssertionError("device accepted a replayed WM attestation")
            assert anchor(index).counter == trusted.counter
            call(index, "sync")
            fresh = anchor(index)
            request = Request(
                config["environment"]["WARD_MANAGER_URL"] + "/ward/attest",
                data=json.dumps(
                    {"wardId": fresh.ward_id.hex(), "nonce": fresh.nonce.hex()}
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request, timeout=10) as response:
                head = json.load(response)
            ward.ingest_attestation(
                session,
                head["counter"],
                bytes.fromhex(head["mac"]) if head.get("mac") else None,
                bytes.fromhex(head["signature"]),
                timestamp=head["timestamp"],
                head_nonce=bytes.fromhex(head["headNonce"]),
            )
            try:
                ward.reconcile(session, b"\x99" * 32)
            except exceptions.TrezorFailure as error:
                assert "root does not match the attested mac" in str(error), str(error)
            else:
                raise AssertionError("device accepted same-counter root substitution")
            assert anchor(index).counter == trusted.counter
            call(index, "sync")
        checked("devices-reject-signed-rollback-and-replayed-attestation")
        checked("same-counter-root-substitution-rejected")
        for index in range(2, len(devices)):
            assert call(index, "sync")["root"] == final["root"]

        if len(devices) >= 3:
            from tools.ward_races import run_races

            run_races(
                config=config,
                devices=devices,
                call=call,
                update=update,
                anchor=anchor,
                pending=pending,
                confirmed=confirmed,
                checked=checked,
            )

        from tools.ward_recovery import run_recovery

        run_recovery(
            config=config,
            devices=devices,
            call=call,
            update=update,
            anchor=anchor,
            pending=pending,
            confirmed=confirmed,
            checked=checked,
        )

    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    results = run(load_config(args.config))
    (args.config.parent / "multi-device-results.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
