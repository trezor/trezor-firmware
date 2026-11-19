"""WARD Manager REST contract, persistence, signatures and concurrent writers."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from tools.ward_manager import DEBUG_SEED, ApiError, WardManager, WardManagerServer
from trezorlib.authdb_tree import root_from_value_digests
from trezorlib.ward_protocol import (
    attestation_message,
    finalization_message,
    transition_message,
)

WALLET_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("12" * 32))
WARD_ID = WALLET_KEY.public_key().public_bytes_raw().hex()
ROOT = "aa" * 32
NONCE = "ab" * 32
MAC = "11" * 32


def signed(counter=1, mac=MAC, root=ROOT, from_root="", from_counter=None):
    record = {
        "wardId": WARD_ID,
        "counter": counter,
        "mac": mac,
        "root": root,
        "fromCounter": counter - 1 if from_counter is None else from_counter,
        "fromRoot": from_root,
        "authCommit": "33" * 32,
        "kind": "commit",
    }
    record["signature"] = WALLET_KEY.sign(transition_message(record)).hex()
    return record


def commit_body(transition, **extra):
    return {"transition": transition, **extra}


@pytest.fixture
def service(tmp_path: Path) -> Iterator[tuple[WardManager, str]]:
    manager = WardManager(tmp_path / "heads.sqlite3", DEBUG_SEED)
    server = WardManagerServer(manager, port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield manager, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        manager.close()


def test_canonical_empty_root_is_used_in_signed_transitions(
    service: tuple[WardManager, str],
) -> None:
    from trezorlib.ward_protocol import EMPTY_ROOT

    _, url = service
    implicit = signed()
    explicit = signed(from_root=EMPTY_ROOT.hex())
    assert transition_message(implicit) == transition_message(explicit)
    accepted = requests.post(
        f"{url}/ward/commit", json=commit_body(explicit), timeout=3
    )
    assert accepted.status_code == 200


def test_attest_commit_and_empty_tree(service: tuple[WardManager, str]) -> None:
    manager, url = service
    public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(manager.public_key))
    health = requests.get(f"{url}/health", timeout=3)
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "publicKey": manager.public_key}

    attested = requests.post(
        f"{url}/ward/attest", json={"wardId": WARD_ID, "nonce": NONCE}, timeout=3
    )
    assert attested.status_code == 200
    assert attested.json().keys() == {"wardId", "nonce", "timestamp", "signature"}
    public_key.verify(
        bytes.fromhex(attested.json()["signature"]),
        attestation_message(WARD_ID, NONCE, 0, None, attested.json()["timestamp"]),
    )

    first = signed()
    committed = requests.post(f"{url}/ward/commit", json=commit_body(first), timeout=3)
    assert committed.status_code == 200
    assert committed.json().keys() == {"wardId", "transition", "signature"}
    assert committed.json()["transition"] == first
    # The finalization signs the whole accepted transition, not only its head.
    final = finalization_message(first)
    assert final.startswith(b"WARD FINAL v1") and final.endswith(
        bytes.fromhex(first["authCommit"])
    )
    public_key.verify(bytes.fromhex(committed.json()["signature"]), final)

    # The attestation returns the latest accepted transition as the head.
    attested = requests.post(
        f"{url}/ward/attest", json={"wardId": WARD_ID, "nonce": NONCE}, timeout=3
    )
    assert attested.status_code == 200
    assert attested.json()["transition"] == first
    assert attested.json()["nonce"] == NONCE
    public_key.verify(
        bytes.fromhex(attested.json()["signature"]),
        attestation_message(WARD_ID, NONCE, 1, MAC, attested.json()["timestamp"]),
    )

    deleted = requests.post(
        f"{url}/ward/commit",
        json=commit_body(signed(counter=2, root="", from_root=ROOT)),
        timeout=3,
    )
    assert deleted.status_code == 200
    assert deleted.json()["transition"]["mac"] == MAC
    history = requests.get(f"{url}/ward/{WARD_ID}/history", timeout=3).json()
    assert history.keys() == {"wardId", "transitions"}
    assert history["transitions"][-1]["root"] == ""
    assert history["transitions"][-1]["counter"] == 2
    assert len(history["transitions"]) == 2
    for record in history["transitions"]:
        WALLET_KEY.public_key().verify(
            bytes.fromhex(record["signature"]), transition_message(record)
        )


def test_stale_commits_return_the_latest_transition(
    service: tuple[WardManager, str],
) -> None:
    _, url = service
    candidate = signed()
    assert (
        requests.post(
            f"{url}/ward/commit", json=commit_body(candidate), timeout=3
        ).status_code
        == 200
    )
    for body in [
        signed(counter=1, mac="22" * 32),
        signed(counter=3, from_root=ROOT),
        signed(counter=2, from_root="bb" * 32),
    ]:
        response = requests.post(
            f"{url}/ward/commit", json=commit_body(body), timeout=3
        )
        assert response.status_code == 409
        assert response.json() == {
            "error": "checkpoint_conflict",
            "wardId": WARD_ID,
            "transition": candidate,
        }


def test_attest_accepts_no_expected_checkpoint(
    service: tuple[WardManager, str],
) -> None:
    _, url = service
    for body in [
        {"wardId": WARD_ID, "counter": 1, "nonce": NONCE},
        {"wardId": WARD_ID, "mac": MAC, "nonce": NONCE},
    ]:
        response = requests.post(f"{url}/ward/attest", json=body, timeout=3)
        assert response.status_code == 400
        assert "signature" not in response.json()


def test_identical_retry_is_idempotent(service: tuple[WardManager, str]) -> None:
    _, url = service
    candidate = commit_body({**signed(), "wardId": WARD_ID.upper()})
    first = requests.post(f"{url}/ward/commit", json=candidate, timeout=3)
    second = requests.post(f"{url}/ward/commit", json=candidate, timeout=3)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    head = requests.get(f"{url}/ward/{WARD_ID}", timeout=3).json()
    assert head == {"wardId": WARD_ID, "transition": signed()}


def test_recovery_requires_independent_predecessor_before_replacing_batch(
    tmp_path: Path,
) -> None:
    key, other = b"\x01" * 32, b"\x02" * 32
    digest, next_digest = b"\x03" * 32, b"\x04" * 32
    predecessor = {key: digest, other: digest}
    replica = {}
    database = tmp_path / "heads.sqlite3"

    def read_replica(ward_id, head, history):
        assert ward_id == WARD_ID
        assert head.counter == 1 and history[0]["root"] == head.root
        return dict(replica)

    manager = WardManager(database, DEBUG_SEED, read_replica)
    server = WardManagerServer(manager, port=0, recovery_read_token="test-recovery")
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/ward"
    root = root_from_value_digests(predecessor).hex()
    batch = [
        {"entryKey": entry_key.hex(), "valueDigest": value_digest.hex()}
        for entry_key, value_digest in predecessor.items()
    ]
    try:
        candidate = commit_body(signed(root=root), recoveryLeaves=batch)
        accepted = requests.post(f"{url}/commit", json=candidate, timeout=3)
        assert accepted.status_code == 200
        retry = requests.post(
            f"{url}/commit",
            json={**candidate, "recoveryLeaves": batch[::-1]},
            timeout=3,
        )
        assert retry.json() == accepted.json()
        assert (
            "recoveryLeaves"
            not in requests.get(f"{url}/{WARD_ID}/history", timeout=3).json()
        )
        assert (
            requests.get(
                f"{url}/{WARD_ID}/history",
                headers={"Authorization": "Bearer test-recovery"},
                timeout=3,
            ).json()["recoveryLeaves"]
            == batch
        )

        next_root = root_from_value_digests({other: next_digest}).hex()
        next_batch = [
            {"entryKey": key.hex(), "valueDigest": None},
            {"entryKey": other.hex(), "valueDigest": next_digest.hex()},
        ]
        successor = signed(counter=2, from_root=root, root=next_root)
        assert (
            requests.post(
                f"{url}/commit", json=commit_body(successor), timeout=3
            ).status_code
            == 400
        )
        candidate = commit_body(successor, recoveryLeaves=next_batch)
        unavailable = requests.post(f"{url}/commit", json=candidate, timeout=3)
        assert unavailable.status_code == 503
        assert (
            manager.history(WARD_ID, include_recovery=True)["recoveryLeaves"] == batch
        )

        replica.update(predecessor)
        wrong = requests.post(
            f"{url}/commit",
            json=commit_body(successor, recoveryLeaves=batch),
            timeout=3,
        )
        assert wrong.status_code == 400
        assert manager.head(WARD_ID)["transition"]["counter"] == 1
        assert (
            requests.post(f"{url}/commit", json=candidate, timeout=3).status_code == 200
        )
        assert manager.head(WARD_ID)["transition"]["counter"] == 2
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        manager.close()

    reopened = WardManager(database, DEBUG_SEED, read_replica)
    try:
        head = reopened.history(WARD_ID, include_recovery=True)
        assert head["transitions"][-1]["root"] == next_root
        assert head["recoveryLeaves"] == next_batch
        assert all("recoveryLeaves" not in row for row in head["transitions"])
    finally:
        reopened.close()


def test_competing_writers_only_one_wins(service: tuple[WardManager, str]) -> None:
    _, url = service
    barrier = threading.Barrier(2)

    def commit(mac: str) -> requests.Response:
        barrier.wait()
        return requests.post(
            f"{url}/ward/commit",
            json=commit_body(signed(mac=mac)),
            timeout=3,
        )

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(commit, [MAC, "22" * 32]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(
        response.json() for response in responses if response.status_code == 200
    )
    loser = next(
        response.json() for response in responses if response.status_code == 409
    )
    assert winner["transition"] == loser["transition"]


def test_persists_heads_and_checks_signing_key(tmp_path: Path) -> None:
    database = tmp_path / "heads.sqlite3"
    manager = WardManager(database, DEBUG_SEED)
    candidate = signed()
    first = manager.commit(commit_body(candidate))
    manager.close()
    restarted = WardManager(database, DEBUG_SEED)
    try:
        assert restarted.commit(commit_body(candidate)) == first
        assert restarted.head(WARD_ID) == {"wardId": WARD_ID, "transition": candidate}
        assert restarted.head("ef" * 32) == {"wardId": "ef" * 32}
    finally:
        restarted.close()
    with pytest.raises(ValueError, match="different WM signing key"):
        WardManager(database, bytes(32))


def test_multiple_manager_connections_share_atomic_cas(tmp_path: Path) -> None:
    database = tmp_path / "heads.sqlite3"
    managers = [WardManager(database, DEBUG_SEED) for _ in range(2)]
    barrier = threading.Barrier(2)

    def commit(index: int) -> int:
        barrier.wait()
        try:
            managers[index].commit(commit_body(signed(mac=f"{index + 1:02x}" * 32)))
        except ApiError as error:
            return error.status
        return 200

    try:
        with ThreadPoolExecutor(2) as pool:
            assert sorted(pool.map(commit, [0, 1])) == [200, 409]
    finally:
        for manager in managers:
            manager.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("fromRoot", "ab" * 32),
        ("root", "ab" * 32),
        ("mac", "ab" * 32),
        ("authCommit", "ab" * 32),
        ("kind", "revert"),
        ("wardId", Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()),
    ],
)
def test_transition_signature_binds_every_operand(service, field, value) -> None:
    manager, url = service
    body = signed()
    body[field] = value
    response = requests.post(f"{url}/ward/commit", json=commit_body(body), timeout=3)
    assert response.status_code == 403
    assert manager.head(WARD_ID) == {"wardId": WARD_ID}
    assert manager.history(WARD_ID)["transitions"] == []


def test_unsigned_and_zero_mac_heads_never_advance_manager(service) -> None:
    manager, url = service
    unsigned = {key: value for key, value in signed().items() if key != "signature"}
    for body in [
        {"wardId": WARD_ID, "counter": 1},
        commit_body(unsigned),
        commit_body({**signed(), "mac": "00" * 32}),
    ]:
        response = requests.post(f"{url}/ward/commit", json=body, timeout=3)
        assert response.status_code == 400
        assert manager.head(WARD_ID) == {"wardId": WARD_ID}


def test_history_is_contiguous_and_cannot_be_rewritten(service) -> None:
    manager, _ = service
    first = signed()
    manager.commit(commit_body(first))
    manager.commit(commit_body(signed(counter=2, from_root=ROOT, root="bb" * 32)))
    with pytest.raises(ApiError) as refused:
        manager.commit(commit_body(signed(root="cc" * 32)))
    assert refused.value.status == 409
    history = manager.history(WARD_ID)
    assert [record["counter"] for record in history["transitions"]] == [1, 2]
    assert history["transitions"][0] == first


def test_signed_freshness_timestamp_never_regresses(service):
    manager, _ = service
    first = manager.attest({"wardId": WARD_ID, "nonce": NONCE})
    public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(manager.public_key))
    public_key.verify(
        bytes.fromhex(first["signature"]),
        attestation_message(WARD_ID, NONCE, 0, None, first["timestamp"]),
    )
    manager.commit(commit_body(signed()))
    second = manager.attest({"wardId": WARD_ID, "nonce": NONCE})
    assert second["timestamp"] >= first["timestamp"]
    assert second["transition"] == signed()
    with pytest.raises(ApiError) as refused:
        manager.commit(commit_body(signed(root="cc" * 32)))
    assert refused.value.status == 409
    assert manager.head(WARD_ID)["transition"]["counter"] == 1


@pytest.mark.parametrize(
    "body",
    [
        [],
        {},
        {"transition": "not-an-object"},
        {"transition": {"wardId": WARD_ID, "counter": 1}},
        commit_body({**signed(), "headNonce": "00" * 32}),
        commit_body({**signed(), "wardId": "not-hex"}),
        commit_body({**signed(), "counter": True}),
        commit_body({**signed(), "counter": -1}),
        commit_body({**signed(), "counter": 2**32}),
        commit_body({**signed(), "counter": 1.5}),
        commit_body({**signed(), "mac": "bad"}),
        commit_body({**signed(), "kind": "merge"}),
        commit_body(signed(), typo="secret"),
        signed(),
    ],
)
def test_rejects_invalid_requests(
    service: tuple[WardManager, str], body: object
) -> None:
    _, url = service
    response = requests.post(f"{url}/ward/commit", json=body, timeout=3)
    assert response.status_code == 400
    assert "signature" not in response.json()
    assert requests.get(f"{url}/ward/{WARD_ID}", timeout=3).json() == {
        "wardId": WARD_ID
    }


def test_http_errors_and_nonce_validation(service: tuple[WardManager, str]) -> None:
    _, url = service
    assert (
        requests.post(f"{url}/ward/commit", data="oops", timeout=3).status_code == 415
    )
    for raw, status in [("{", 400), (" " * 4097, 413)]:
        response = requests.post(
            f"{url}/ward/commit",
            data=raw,
            headers={"Content-Type": "application/json"},
            timeout=3,
        )
        assert response.status_code == status
    assert requests.get(f"{url}/missing", timeout=3).status_code == 404
    assert requests.get(f"{url}/ward/attest", timeout=3).status_code == 405
    assert requests.get(f"{url}/ward/commit", timeout=3).status_code == 405
    assert requests.put(f"{url}/ward/commit", timeout=3).status_code == 405
    for body in [{"wardId": WARD_ID}, {"wardId": WARD_ID, "nonce": "00"}]:
        assert (
            requests.post(f"{url}/ward/attest", json=body, timeout=3).status_code == 400
        )


def test_logs_correlated_requests_and_responses(
    service: tuple[WardManager, str], caplog: pytest.LogCaptureFixture
) -> None:
    _, url = service
    caplog.set_level(logging.INFO, logger="ward-manager")
    request = commit_body(signed())
    response = requests.post(f"{url}/ward/commit", json=request, timeout=3)
    records = [json.loads(record.message) for record in caplog.records]
    assert [record["event"] for record in records] == [
        "request",
        "request_body",
        "response",
    ]
    assert {record["id"] for record in records} == {response.headers["X-Request-ID"]}
    assert records[0]["method"] == "POST"
    assert records[0]["path"] == "/ward/commit"
    assert records[1]["body"] == request
    assert records[2]["body"] == response.json()
    assert records[2]["status"] == 200
    assert records[2]["durationMs"] >= 0


def test_storage_failure_returns_no_signature(service: tuple[WardManager, str]) -> None:
    manager, url = service
    manager.close()
    response = requests.post(
        f"{url}/ward/commit",
        json=commit_body(signed()),
        timeout=3,
    )
    assert response.status_code == 503
    assert response.json() == {"error": "storage_unavailable"}


def test_logs_unsupported_methods_and_head(
    service: tuple[WardManager, str], caplog: pytest.LogCaptureFixture
) -> None:
    _, url = service
    caplog.set_level(logging.INFO, logger="ward-manager")
    for method, expected in [("HEAD", 200), ("OPTIONS", 405), ("BREW", 405)]:
        response = requests.request(method, f"{url}/health", timeout=3)
        assert response.status_code == expected
        assert response.headers["X-Request-ID"]
        if method == "HEAD":
            assert response.content == b""
    records = [json.loads(record.message) for record in caplog.records]
    assert [record["method"] for record in records if record["event"] == "request"] == [
        "HEAD",
        "OPTIONS",
        "BREW",
    ]
    assert len([record for record in records if record["event"] == "response"]) == 3
    assert all("time" in record for record in records)


def test_logs_http_parser_rejections(
    service: tuple[WardManager, str], caplog: pytest.LogCaptureFixture
) -> None:
    _, url = service
    caplog.set_level(logging.INFO, logger="ward-manager")
    port = urlparse(url).port
    assert port is not None
    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
        connection.sendall(b"GET /health HTTP/invalid\r\n\r\n")
        while connection.recv(4096):
            pass
    records = [json.loads(record.message) for record in caplog.records]
    assert [record["event"] for record in records] == ["request", "response"]
    assert records[0]["id"] == records[1]["id"]
    assert records[1]["status"] == 400
    assert all("time" in record for record in records)


def test_delayed_responses_wait_before_sending(tmp_path: Path) -> None:
    manager = WardManager(tmp_path / "delayed.sqlite3", DEBUG_SEED)
    try:
        with WardManagerServer(manager, port=0, delays=True) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                started = time.monotonic()
                response = requests.get(
                    f"http://127.0.0.1:{server.server_port}/health", timeout=5
                )
                assert response.status_code == 200
                assert time.monotonic() - started >= 1
            finally:
                server.shutdown()
                thread.join()
    finally:
        manager.close()
