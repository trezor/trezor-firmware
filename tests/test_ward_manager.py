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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tools.ward_manager import DEBUG_SEED, ApiError, WardManager, WardManagerServer

WARD_ID = "cd" * 32
NONCE = "ab" * 32
MAC = "11" * 32


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
    assert attested.json()["counter"] == 0
    public_key.verify(
        bytes.fromhex(attested.json()["signature"]),
        b"WARD ATTEST v1\x01" + bytes.fromhex(NONCE + WARD_ID) + bytes(4) + bytes(32),
    )

    committed = requests.post(
        f"{url}/ward/commit",
        json={"wardId": WARD_ID, "counter": 1, "mac": MAC},
        timeout=3,
    )
    assert committed.status_code == 200
    public_key.verify(
        bytes.fromhex(committed.json()["signature"]),
        b"WARD FINAL v1"
        + bytes.fromhex(WARD_ID)
        + (1).to_bytes(4, "big")
        + bytes.fromhex(MAC),
    )

    # The existing HttpWm client supplies the checkpoint it expects to be signed.
    checkpoint = {"wardId": WARD_ID, "counter": 1, "mac": MAC, "nonce": NONCE}
    attested = requests.post(f"{url}/ward/attest", json=checkpoint, timeout=3)
    assert attested.status_code == 200
    public_key.verify(
        bytes.fromhex(attested.json()["signature"]),
        b"WARD ATTEST v1\x01"
        + bytes.fromhex(NONCE + WARD_ID)
        + (1).to_bytes(4, "big")
        + bytes.fromhex(MAC),
    )

    deleted = requests.post(
        f"{url}/ward/commit", json={"wardId": WARD_ID, "counter": 2}, timeout=3
    )
    assert deleted.status_code == 200
    assert "mac" not in deleted.json()
    public_key.verify(
        bytes.fromhex(deleted.json()["signature"]),
        b"WARD FINAL v1" + bytes.fromhex(WARD_ID) + (2).to_bytes(4, "big") + bytes(32),
    )
    empty_attestation = requests.post(
        f"{url}/ward/attest",
        json={"wardId": WARD_ID, "nonce": NONCE, "counter": 2, "mac": "00" * 32},
        timeout=3,
    )
    assert empty_attestation.status_code == 200
    assert empty_attestation.json()["counter"] == 2
    assert "mac" not in empty_attestation.json()


def test_rejects_forged_attestations_and_stale_commits(
    service: tuple[WardManager, str],
) -> None:
    _, url = service
    candidate = {"wardId": WARD_ID, "counter": 1, "mac": MAC}
    assert (
        requests.post(f"{url}/ward/commit", json=candidate, timeout=3).status_code
        == 200
    )
    for endpoint, body in [
        ("attest", {"wardId": WARD_ID, "counter": 7, "mac": MAC, "nonce": NONCE}),
        ("attest", {"wardId": WARD_ID, "counter": 1, "nonce": NONCE}),
        ("commit", {"wardId": WARD_ID, "counter": 0}),
        ("commit", {"wardId": WARD_ID, "counter": 3, "mac": MAC}),
        ("commit", {"wardId": WARD_ID, "counter": 1, "mac": "22" * 32}),
    ]:
        response = requests.post(f"{url}/ward/{endpoint}", json=body, timeout=3)
        assert response.status_code == 409
        assert response.json() == {
            "error": "checkpoint_conflict",
            "counter": 1,
            "mac": MAC,
        }
        assert "signature" not in response.json()


def test_identical_retry_is_idempotent(service: tuple[WardManager, str]) -> None:
    _, url = service
    candidate = {"wardId": WARD_ID.upper(), "counter": 1, "mac": MAC}
    first = requests.post(f"{url}/ward/commit", json=candidate, timeout=3)
    second = requests.post(f"{url}/ward/commit", json=candidate, timeout=3)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert requests.get(f"{url}/ward/{WARD_ID}", timeout=3).json() == {
        "wardId": WARD_ID,
        "counter": 1,
        "mac": MAC,
    }


def test_competing_writers_only_one_wins(service: tuple[WardManager, str]) -> None:
    _, url = service
    barrier = threading.Barrier(2)

    def commit(mac: str) -> requests.Response:
        barrier.wait()
        return requests.post(
            f"{url}/ward/commit",
            json={"wardId": WARD_ID, "counter": 1, "mac": mac},
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
    assert winner["mac"] == loser["mac"]


def test_persists_heads_and_checks_signing_key(tmp_path: Path) -> None:
    database = tmp_path / "heads.sqlite3"
    manager = WardManager(database, DEBUG_SEED)
    candidate = {"wardId": WARD_ID, "counter": 1, "mac": MAC}
    first = manager.commit(candidate)
    manager.close()
    restarted = WardManager(database, DEBUG_SEED)
    try:
        assert restarted.commit(candidate) == first
        assert restarted.head(WARD_ID) == {"wardId": WARD_ID, "counter": 1, "mac": MAC}
        assert restarted.head("ef" * 32) == {"wardId": "ef" * 32, "counter": 0}
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
            managers[index].commit(
                {"wardId": WARD_ID, "counter": 1, "mac": f"{index + 1:02x}" * 32}
            )
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
    "body",
    [
        [],
        {},
        {"wardId": "not-hex", "counter": 1},
        {"wardId": WARD_ID, "counter": True},
        {"wardId": WARD_ID, "counter": -1},
        {"wardId": WARD_ID, "counter": 2**32},
        {"wardId": WARD_ID, "counter": 1.5},
        {"wardId": WARD_ID, "counter": 1, "mac": "bad"},
        {"wardId": WARD_ID, "counter": 1, "typo": "secret"},
    ],
)
def test_rejects_invalid_requests(
    service: tuple[WardManager, str], body: object
) -> None:
    _, url = service
    response = requests.post(f"{url}/ward/commit", json=body, timeout=3)
    assert response.status_code == 400
    assert "signature" not in response.json()
    assert requests.get(f"{url}/ward/{WARD_ID}", timeout=3).json()["counter"] == 0


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
    request = {"wardId": WARD_ID, "counter": 1, "mac": MAC}
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
        json={"wardId": WARD_ID, "counter": 1, "mac": MAC},
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
