"""The Rust engine, through both Python host imports, on one HWI session."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trezorlib import messages, protobuf
from trezorlib.debuglink import DebugSession

from . import test_ward_relay as relay

pytestmark = relay.pytestmark
wardd = relay.wardd
wardd_port = relay.wardd_port
wm_url = relay.wm_url


@pytest.mark.parametrize("binding", ("ward_relay", "jadepy.ward"))
def test_ward_handoff_on_hwi_session(
    session: DebugSession,
    wardd,
    wardd_port: int,
    tmp_path: Path,
    binding: str,
    capfd: pytest.CaptureFixture,
) -> None:
    module = pytest.importorskip(binding)
    pulls = []
    previous = session.client.app.ward_proof_callback
    with module.WardAdapter(
        token=(tmp_path / "token").read_text(),
        url=f"ws://127.0.0.1:{wardd_port}",
    ) as adapter:

        def proof(request):
            pulls.append(request)
            reply = adapter.answer_ward_request(
                type(request).__name__, protobuf.to_dict(request)
            )
            assert reply["name"] == "WARDProofAck"
            return protobuf.dict_to_proto(messages.WARDProofAck, reply["message"])

        def device_call(name, body):
            # Only this HWI callback owns device I/O; the adapter sees JSON protobufs.
            request = protobuf.dict_to_proto(getattr(messages, name), body)
            response = session.call(request)
            return type(response).__name__, protobuf.to_dict(response)

        session.client.app.ward_proof_callback = proof
        try:
            assert adapter.call("sync", {}, device_call)["counter"] == 0
            params = {
                "appId": "bitcoin",
                "address": "bc1qshared",
                "networkSymbol": "btc",
            }
            written = relay._confirmed(
                session,
                lambda _: adapter.call(
                    "update",
                    {**params, "metadata": {"label": "shared adapter"}},
                    device_call,
                ),
            )
            assert written["counter"] == 1
            found = adapter.call("lookup", params, device_call)
            assert found["valid"] and found["isMember"]
            assert found["metadata"] == {"label": "shared adapter"}
            assert pulls
        finally:
            session.client.app.ward_proof_callback = previous
    logs = [
        json.loads(line)
        for line in capfd.readouterr().err.splitlines()
        if line.startswith("{")
    ]
    assert logs and all(
        "time" in event and event["service"] == "ward-adapter" for event in logs
    )
    assert "shared adapter" not in json.dumps(logs)
