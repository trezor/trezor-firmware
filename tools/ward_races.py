"""Real-device races using genuine candidates and confirmations from the running WM."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools.ward_stack import debug_request
from trezorlib import exceptions, messages


def run_races(
    *,
    config: dict[str, Any],
    devices: list,
    call: Callable,
    update: Callable,
    anchor: Callable,
    pending: Callable,
    confirmed: Callable,
    checked: Callable,
) -> None:
    def log(event: str, **fields: Any) -> None:
        print(
            json.dumps(
                {
                    "time": datetime.now(timezone.utc).isoformat(
                        timespec="milliseconds"
                    ),
                    "service": "WARD race tests",
                    "event": event,
                    **fields,
                }
            ),
            flush=True,
        )

    def request(path: str, payload: dict | None = None) -> tuple[int, dict]:
        message = Request(
            config["environment"]["WARD_MANAGER_URL"] + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(message, timeout=15) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def snapshot(index: int) -> tuple:
        state = anchor(index)
        return state.counter, state.root, state.root_known, tuple(pending(index))

    def reject(
        index: int, confirmation: dict, reason: str, *, source: int | None = None
    ) -> None:
        before = snapshot(index)
        log(
            "race.confirmation.send",
            source=None if source is None else f"device-{source + 1}",
            target=f"device-{index + 1}",
            counter=confirmation["counter"],
            expectedRejection=reason,
        )
        try:
            devices[index][1].call(
                messages.WARDConfirmBatchByWM(**confirmation),
                expect=messages.WARDConfirmBatchByWMAck,
            )
        except exceptions.TrezorFailure as error:
            assert reason in str(error), str(error)
            log(
                "race.confirmation.rejected",
                target=f"device-{index + 1}",
                reason=str(error),
            )
        else:
            raise AssertionError(f"device-{index + 1} accepted a crossed confirmation")
        assert snapshot(index) == before, (
            "rejection changed the anchor or pending queue"
        )

    def round_trip(round_id: int, elected: int | None) -> None:
        log(
            "race.start",
            round=round_id,
            elected=None if elected is None else f"device-{elected + 1}",
        )
        for index in range(3):
            call(index, "sync")
            assert not pending(index)
        base = [snapshot(index) for index in range(3)]
        assert all(state[:3] == base[0][:3] for state in base)
        prefix = f"ward-race-{round_id}"
        candidates: dict[int, dict] = {}
        attestations: dict[int, dict] = {}

        def prepare(index: int, address: str, label: str) -> None:
            forwarding = devices[index][2]
            previous = forwarding.forward

            def intercept(name: str, body: dict):
                if name == "WARDIngestAttestation":
                    attestations[index] = dict(body)
                response_name, response = previous(name, body)
                if (
                    name == "WARDPerformBatch"
                    and response_name == "WARDPerformBatchAck"
                ):
                    candidates[index] = dict(response)
                    # This channel remains responsive while wardd awaits the device reply.
                    assert debug_request(config, "PAUSE", f"device-{index + 1}")[
                        "paused"
                    ]
                return response_name, response

            forwarding.forward = intercept
            try:
                result = update(index, address, label)
                assert result.get("queued"), result
            finally:
                forwarding.forward = previous
            assert index in candidates
            assert snapshot(index)[:3] == base[index][:3]
            log(
                "race.candidate.withheld",
                device=f"device-{index + 1}",
                counter=candidates[index]["counter"],
            )

        try:
            # Both intents are on device-1; Suite persists its candidate but withholds WM publication.
            prepare(0, prefix + "-A", "A from device-1")
            assert update(0, prefix + "-B", "B from device-1").get("queued")
            assert len(pending(0)) == 2
            prepare(1, prefix + "-A", "A from device-2")
            prepare(2, prefix + "-C", "C from device-3")
            ward_id = candidates[0]["ward_id"]
            assert len({candidate["counter"] for candidate in candidates.values()}) == 1
            assert candidates[0]["counter"] == base[0][0] + 1
            assert len({candidate["mac"] for candidate in candidates.values()}) == 3
            status, history_before = request(f"/ward/{ward_id}/history")
            assert status == 200
            status, wm_before = request(
                "/ward/attest", {"wardId": ward_id, "nonce": "ab" * 32}
            )
            assert status == 200 and wm_before["counter"] == base[0][0]

            records = []
            for index in range(3):
                candidate = candidates[index]
                records.append(
                    {
                        "wardId": ward_id,
                        "fromCounter": candidate["counter"] - 1,
                        "fromRoot": candidate["from_root"],
                        "counter": candidate["counter"],
                        "root": candidate.get("new_root", ""),
                        "mac": candidate["mac"],
                        "authCommit": candidate["auth_commit"],
                        "signature": candidate["sig_commit"],
                        "headNonce": attestations[index]["head_nonce"],
                        "kind": "commit",
                    }
                )
            if elected is None:
                barrier = threading.Barrier(3)

                def submit(index: int):
                    barrier.wait(timeout=15)
                    return request("/ward/commit", records[index])

                with ThreadPoolExecutor(max_workers=3) as workers:
                    responses = list(workers.map(submit, range(3)))
                assert sorted(status for status, _ in responses) == [200, 409, 409]
                winner = next(
                    index
                    for index, (status, _) in enumerate(responses)
                    if status == 200
                )
                accepted = responses[winner][1]
            else:
                winner = elected
                status, accepted = request("/ward/commit", records[winner])
                assert status == 200, accepted
                for index in range(3):
                    if index != winner:
                        status, _ = request("/ward/commit", records[index])
                        assert status == 409, "WM accepted a competing successor"
            status, history = request(f"/ward/{ward_id}/history")
            assert status == 200
            assert len(history["transitions"]) == len(history_before["transitions"]) + 1
            assert history["transitions"][-1]["root"] == records[winner]["root"]
            log(
                "race.wm.accepted",
                device=f"device-{winner + 1}",
                counter=candidates[winner]["counter"],
                rejectedCompetitors=2,
            )
            confirmation = {
                "counter": candidates[winner]["counter"],
                "mac": bytes.fromhex(candidates[winner]["mac"]),
                "wm_signature": bytes.fromhex(accepted["signature"]),
            }
            for index in range(3):
                if index == winner:
                    continue
                reject(
                    index,
                    confirmation,
                    "confirmation does not match the committed batch",
                    source=winner,
                )
                # Matching the recipient's MAC cannot make the other candidate's WM signature valid.
                reject(
                    index,
                    {**confirmation, "mac": bytes.fromhex(candidates[index]["mac"])},
                    "WM final attestation verification failed",
                )
            # A device's own transition signature is not a WM confirmation either.
            reject(
                winner,
                {
                    **confirmation,
                    "wm_signature": bytes.fromhex(candidates[winner]["sig_commit"]),
                },
                "WM final attestation verification failed",
            )
            installed = devices[winner][1].call(
                messages.WARDConfirmBatchByWM(**confirmation),
                expect=messages.WARDConfirmBatchByWMAck,
            )
            assert installed.counter == base[0][0] + 1
            reject(winner, confirmation, "no committed batch to finalize")
            # Exact publication retries are idempotent and do not produce another history row.
            status, retried = request("/ward/commit", records[winner])
            assert status == 200 and retried["signature"] == accepted["signature"]
        finally:
            for index in range(3):
                debug_request(config, "CONTINUE", f"device-{index + 1}")

        # The losing envelopes and the unrelated B intent must survive all cross-deliveries.
        for index in range(3):
            call(index, "sync")
        final = [call(index, "sync") for index in range(3)]
        assert len({(head["counter"], head["root"]) for head in final}) == 1
        assert final[0]["counter"] == base[0][0] + 4
        assert all(not pending(index) for index in range(3))
        for index in range(3):
            for suffix in ("A", "B", "C"):
                result = call(
                    index,
                    "lookup",
                    {
                        "appId": "bitcoin",
                        "address": prefix + "-" + suffix,
                        "networkSymbol": "btc",
                    },
                )
                assert result["valid"] and result["isMember"]
        confirmed(
            2,
            lambda: devices[2][1].call(
                messages.DisplayAddress(address=prefix + "-A", app_id="bitcoin")
            ),
            "A from device-1" if winner == 1 else "A from device-2",
        )
        status, history = request(f"/ward/{ward_id}/history")
        assert status == 200
        assert len(history["transitions"]) == len(history_before["transitions"]) + 4
        log(
            "race.converged",
            round=round_id,
            counter=final[0]["counter"],
            devices=3,
            pending=0,
        )
        # Delayed old confirmations also fail after the recipient has caught up.
        for index in range(3):
            reject(index, confirmation, "no committed batch to finalize")

    for number, (winner, name) in enumerate(
        [
            (1, "cross-confirmations-device-2-to-device-1"),
            (0, "cross-confirmations-device-1-to-device-2"),
            (None, "three-device-concurrent-publication"),
        ]
    ):
        round_trip(number, winner)
        checked(name)
