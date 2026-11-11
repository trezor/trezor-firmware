"""The same authenticated WARD flows over independent service and wallet transports."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from trezorlib.debuglink import DebugSession as Session
from trezorlib.ward_relay import WardAdapter, WarddClient
from trezorlib.ward_service import WardService, ward_transport

from . import test_ward_relay as relay_helpers
from .test_ward_relay import APP, NETWORK, SUITE_DIR, _confirmed

wardd = relay_helpers.wardd
wardd_port = relay_helpers.wardd_port
wm_url = relay_helpers.wm_url

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.skipif(not SUITE_DIR, reason="WARDD_SUITE_DIR is not set"),
]


@pytest.mark.parametrize(
    "use_service", [True, False], ids=["service", "wallet-fallback"]
)
def test_independent_service_and_wallet_fallback(
    session: Session,
    wardd: WarddClient,
    wardd_port: int,
    tmp_path: Path,
    use_service: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wallet_proofs = []
    original_call = wardd.call
    require_service = use_service

    def wallet_call(method, params=None, device=None):
        if method in ("answerProofRequest", "answerNodeRequest"):
            wallet_proofs.append(method)
            assert not require_service, "backend data crossed the wallet interface"
        return original_call(method, params, device)

    monkeypatch.setattr(wardd, "call", wallet_call)
    adapter = WardAdapter(session, wardd)
    backend = WarddClient(
        token=(tmp_path / "token").read_text(),
        url=f"ws://127.0.0.1:{wardd_port}",
    )
    service = WardService(ward_transport(session.client.transport), backend)
    try:
        if use_service:
            service.open()
        with service.serving() if use_service else nullcontext():
            assert adapter.sync()["counter"] == 0
            for counter, address in enumerate(("bc1qservice-a", "bc1qservice-b"), 1):
                result = _confirmed(
                    session,
                    lambda current, address=address: WardAdapter(current, wardd).update(
                        APP,
                        address,
                        NETWORK,
                        {"label": address},
                    ),
                )
                assert result["counter"] == counter
            found = adapter.lookup(APP, "bc1qservice-a", NETWORK)
            assert found["valid"] and found["isMember"]
            _confirmed(
                session,
                lambda current: WardAdapter(current, wardd).display_address(
                    APP, "bc1qservice-a"
                ),
            )
            if use_service:
                backend_call = backend.call

                def corrupt_proof(method, params=None, device=None):
                    reply = backend_call(method, params, device)
                    if method == "answerProofRequest" and reply.get("proof"):
                        proof = list(reply["proof"])
                        altered = bytearray.fromhex(proof[0])
                        altered[-1] ^= 1
                        proof[0] = altered.hex()
                        reply = {**reply, "proof": proof}
                    return reply

                with monkeypatch.context() as patch:
                    patch.setattr(backend, "call", corrupt_proof)
                    rejected = adapter.lookup(APP, "bc1qservice-a", NETWORK)
                    assert not rejected["valid"]
                healthy = adapter.lookup(APP, "bc1qservice-a", NETWORK)
                assert healthy["valid"] and healthy["counter"] == 2
            absent = adapter.lookup(APP, "bc1qservice-missing", NETWORK)
            assert absent["valid"] and not absent["isMember"]
            deleted = _confirmed(
                session,
                lambda current: WardAdapter(current, wardd).update(
                    APP,
                    "bc1qservice-a",
                    NETWORK,
                    delete=True,
                ),
            )
            assert deleted["counter"] == 3
        if use_service:
            assert "WARDSyncAck" in service.served
            assert "WARDProofRequest" in service.served
            assert "WARDPerformBatchAck" in service.served
            assert not wallet_proofs
            service.close()
            require_service = False
            # The very next workflow must fall back, using the same published replica.
            result = adapter.lookup(APP, "bc1qservice-b", NETWORK)
            assert result["valid"] and result["isMember"]
            service.open()
            require_service = True
            with service.serving():
                rebound = adapter.lookup(APP, "bc1qservice-b", NETWORK)
                assert rebound["valid"] and rebound["isMember"]
        assert wallet_proofs
    finally:
        if service.bound:
            service.close()
        backend.close()


def test_wardd_connects_directly_to_service_channel(
    session: Session,
    wardd_port: int,
    wm_url: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os
    import secrets
    import subprocess

    from trezorlib import messages

    assert SUITE_DIR is not None
    token = secrets.token_hex(16)
    token_file = tmp_path / "token"
    token_file.write_text(token)
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in ("WARD_MANAGER_URL", "WARD_MANAGER_PORT")
    }
    process = subprocess.Popen(
        [
            "node",
            "--import",
            "tsx",
            "src/cli.ts",
            "--memory",
            "--port",
            str(wardd_port),
            "--data-dir",
            str(tmp_path / "wardd-native"),
            "--token-file",
            str(token_file),
            "--service-channel",
            session.client.transport.get_path(),
            *(["--wm-url", wm_url] if wm_url else []),
        ],
        cwd=Path(SUITE_DIR) / "packages" / "wardd",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert process.stdout is not None
        line = process.stdout.readline()
        assert "WARD service connected" in line, line + process.stdout.read()
        with WarddClient(token=token, url=f"ws://127.0.0.1:{wardd_port}") as backend:
            original = backend.call

            def wallet_call(method, params=None, device=None):
                assert method not in ("answerProofRequest", "answerNodeRequest")
                return original(method, params, device)

            monkeypatch.setattr(backend, "call", wallet_call)
            adapter = WardAdapter(session, backend)
            assert adapter.sync()["counter"] == 0
            result = _confirmed(
                session,
                lambda current: WardAdapter(current, backend).update(
                    APP, "bc1qnative-service", NETWORK, {"label": "native service"}
                ),
            )
            assert result["counter"] == 1
            found = adapter.lookup(APP, "bc1qnative-service", NETWORK)
            assert found["valid"] and found["isMember"]
            _confirmed(
                session,
                lambda current: WardAdapter(current, backend).display_address(
                    APP, "bc1qnative-service"
                ),
            )
            deleted = _confirmed(
                session,
                lambda current: WardAdapter(current, backend).update(
                    APP, "bc1qnative-service", NETWORK, delete=True
                ),
            )
            assert deleted["counter"] == 2
        process.terminate()
        assert process.wait(timeout=10) == 0
        # A clean wardd shutdown releases the binding even though the wallet remains connected.
        state = session.call(messages.WARDSync(), expect=messages.WARDSyncAck)
        assert not state.service_bound
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
