"""Recover real devices from a missing Evolu leaf publication using an authorized revert."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from tools.ward_stack import debug_request
from trezorlib import exceptions, messages


def run_recovery(
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
    from ward_relay import WardAdapter

    def request(path: str, payload: dict | None = None) -> dict:
        with urlopen(
            Request(
                config["environment"]["WARD_MANAGER_URL"] + path,
                data=None if payload is None else json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=15,
        ) as response:
            return json.load(response)

    heads = [call(index, "sync") for index in range(len(devices))]
    assert len({(head["counter"], head["root"]) for head in heads}) == 1
    assert all(not pending(index) for index in range(len(devices)))
    ward_id = heads[0]["wardId"]
    before = debug_request(config, "RECONSTRUCT", wardId=ward_id)
    assert before["complete"]
    captured: dict[str, dict] = {}
    forwarding = devices[0][2]
    previous = forwarding.forward

    def intercept(name: str, body: dict):
        if name == "WARDIngestAttestation":
            captured["attestation"] = dict(body)
        response_name, response = previous(name, body)
        if name == "WARDPerformBatch" and response_name == "WARDPerformBatchAck":
            captured["candidate"] = dict(response)
            debug_request(config, "PAUSE", "device-1")
        return response_name, response

    forwarding.forward = intercept
    try:
        result = update(
            0, "ward-lost-evolu-entry", "entry whose publication will be lost"
        )
        assert result.get("queued") and len(pending(0)) == 1
    finally:
        forwarding.forward = previous
    candidate = captured["candidate"]
    publication = {
        "wardId": ward_id,
        "fromCounter": candidate["counter"] - 1,
        "fromRoot": candidate["from_root"],
        "counter": candidate["counter"],
        "root": candidate["new_root"],
        "mac": candidate["mac"],
        "authCommit": candidate["auth_commit"],
        "signature": candidate["sig_commit"],
        "headNonce": captured["attestation"]["head_nonce"],
        "kind": "commit",
    }
    accepted = request("/ward/commit", publication)
    cached = {
        "counter": candidate["counter"],
        "mac": candidate["mac"],
        "wm_signature": accepted["signature"],
    }
    # Delete the journal row containing the leaf, not merely the redundant current-entry cache.
    assert debug_request(
        config,
        "DROP_TRANSITION",
        wardId=ward_id,
        counter=candidate["counter"],
        root=candidate["new_root"],
    )["dropped"]
    partial = debug_request(config, "RECONSTRUCT", wardId=ward_id)
    assert not partial["complete"] and partial["missingCounter"] == candidate["counter"]
    assert (partial["counter"], partial["root"], partial["entries"]) == (
        before["counter"],
        before["root"],
        before["entries"],
    )
    assert partial["headCounter"] == before["counter"] + 1
    checked("recovery-reconstructs-last-complete-prefix-after-evolu-loss")
    token = Path(config["environment"]["WARD_TOKEN_FILE"]).read_text().strip()
    observer = anchor(1)
    with WardAdapter(token=token, url=config["environment"]["WARDD_URL"]) as adapter:
        adapter.set_logging(False)
        with adapter.session(devices[1][1]) as host:
            try:
                host.call("sync", {"debugDeviceId": "device-2"})
            except RuntimeError as error:
                assert "incomplete" in str(error) or "unavailable data" in str(error), (
                    str(error)
                )
            else:
                raise AssertionError(
                    "normal sync adopted a head whose trie cannot be rebuilt"
                )
    assert (anchor(1).counter, anchor(1).root) == (observer.counter, observer.root)

    # Cached confirmations remain cryptographically checked before they establish a stuck head.
    try:
        devices[0][1].call(
            messages.WARDConfirmBatchByWM(
                counter=cached["counter"],
                mac=bytes.fromhex(cached["mac"]),
                wm_signature=b"\x00" * 64,
            )
        )
    except exceptions.TrezorFailure as error:
        assert "WM final attestation verification failed" in str(error)
    else:
        raise AssertionError("device accepted a forged cached confirmation")
    assert anchor(0).counter == before["counter"] and pending(0)
    debug_request(config, "CONTINUE", "device-1")
    token = Path(config["environment"]["WARD_TOKEN_FILE"]).read_text().strip()

    def recover(approve: bool):
        # A fresh wardd endpoint and a newly built trie, with no reliance on the old host snapshot.
        with WardAdapter(
            token=token, url=config["environment"]["WARDD_URL"]
        ) as adapter:
            adapter.set_logging(False)
            with adapter.session(devices[0][1]) as host:
                return confirmed(
                    0,
                    lambda: host.call(
                        "sync",
                        {
                            "recover": True,
                            "cachedConfirmation": cached,
                            "debugDeviceId": "device-1",
                        },
                    ),
                    approve=approve,
                )

    try:
        recover(False)
    except RuntimeError as error:
        assert "cancel" in str(error).lower(), str(error)
    else:
        raise AssertionError("rollback proceeded without user approval")
    head = request("/ward/attest", {"wardId": ward_id, "nonce": "ab" * 32})
    assert (
        head["counter"] == candidate["counter"]
        and head["root"] == candidate["new_root"]
    )
    assert anchor(0).counter == candidate["counter"]
    assert anchor(1).counter == before["counter"]
    assert not debug_request(config, "RECONSTRUCT", wardId=ward_id)["complete"]
    checked("recovery-cached-confirmation-does-not-bypass-user-approval")
    recovered = recover(True)
    assert (
        recovered["root"] == before["root"]
        and recovered["counter"] == before["counter"] + 2
    )
    rebuilt = debug_request(config, "RECONSTRUCT", wardId=ward_id)
    assert (
        rebuilt["complete"]
        and rebuilt["root"] == before["root"]
        and rebuilt["entries"] == before["entries"]
    )
    assert rebuilt["counter"] == recovered["counter"]
    history = request(f"/ward/{ward_id}/history")["transitions"]
    assert (
        history[-1]["kind"] == "revert"
        and history[-1]["fromRoot"] == candidate["new_root"]
    )
    assert history[-1]["root"] == before["root"]
    for index in range(1, len(devices)):
        caught_up = call(index, "sync")
        assert (caught_up["counter"], caught_up["root"]) == (
            recovered["counter"],
            recovered["root"],
        )
        missing = call(
            index,
            "lookup",
            {
                "appId": "bitcoin",
                "address": "ward-lost-evolu-entry",
                "networkSymbol": "btc",
            },
        )
        assert missing["valid"] and not missing["isMember"]
    checked("recovery-second-device-verifies-rollback-in-history")
    # Recovery must also restore the ability to publish and prove subsequent edits.
    successor = update(1, "ward-after-recovery", "new edit after rollback")
    assert successor["counter"] == recovered["counter"] + 1
    for index in range(len(devices)):
        assert call(index, "sync")["root"] == successor["root"]
        assert not pending(index)
    checked("recovery-rebuilds-trie-and-allows-new-writes")
