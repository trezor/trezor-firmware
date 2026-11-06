"""The shared adapter owns forwarding; wallet imports are aliases only."""

from types import SimpleNamespace

import pytest


def test_jade_only_reexports_the_shared_adapter():
    jade = pytest.importorskip("jadepy.ward")
    shared = pytest.importorskip("ward_relay")
    assert jade.WardHwi is shared.WardHwi
    assert jade.WardAdapter is shared.WardAdapter


def test_adapter_attaches_to_a_borrowed_session():
    shared = pytest.importorskip("ward_relay")
    previous = object()
    app = SimpleNamespace(ward_proof_callback=previous, ward_node_callback=previous)
    session = SimpleNamespace(client=SimpleNamespace(app=app))
    adapter = shared.WardAdapter.__new__(shared.WardAdapter)
    with adapter.session(session) as hwi:
        assert hwi.session is session
        assert hwi.adapter is adapter
        assert app.ward_proof_callback == hwi._pull
        assert app.ward_node_callback == hwi._pull
    assert app.ward_proof_callback is previous
    assert app.ward_node_callback is previous


def test_borrowed_jade_session_restores_callback_after_failure():
    module = pytest.importorskip("jadepy.ward")
    previous = object()
    app = SimpleNamespace(ward_proof_callback=previous, ward_node_callback=previous)
    session = SimpleNamespace(client=SimpleNamespace(app=app))
    adapter = SimpleNamespace()
    hwi = module.WardHwi(session, adapter)
    with pytest.raises(RuntimeError, match="context manager"):
        hwi.call("sync", {})
    with pytest.raises(ValueError, match="caller failed"):
        with hwi:
            assert app.ward_proof_callback != previous
            with pytest.raises(RuntimeError, match="already active"):
                hwi.__enter__()
            raise ValueError("caller failed")
    assert app.ward_proof_callback is previous
    assert hwi.session is session


def test_adapter_preserves_device_failure_for_rollback_diagnostics():
    from trezorlib import exceptions, messages

    shared = pytest.importorskip("ward_relay")
    failure = messages.Failure(
        code=messages.FailureType.DataError,
        message="attested counter is older than counter_loc",
    )

    def refused(_):
        raise exceptions.TrezorFailure(failure)

    app = SimpleNamespace(ward_proof_callback=None, ward_node_callback=None)
    session = SimpleNamespace(client=SimpleNamespace(app=app), call=refused)
    adapter = shared.WardAdapter.__new__(shared.WardAdapter)
    with adapter.session(session) as hwi:
        name, body = hwi.forward("WARDSync", {})
    assert name == "Failure"
    assert body["message"] == failure.message


def test_adapter_preserves_user_cancellation_for_recovery():
    from trezorlib import exceptions, messages, protobuf

    shared = pytest.importorskip("ward_relay")

    def cancelled(_):
        raise exceptions.Cancelled("User declined rollback")

    app = SimpleNamespace(ward_proof_callback=None, ward_node_callback=None)
    session = SimpleNamespace(client=SimpleNamespace(app=app), call=cancelled)
    adapter = shared.WardAdapter.__new__(shared.WardAdapter)
    with adapter.session(session) as hwi:
        name, body = hwi.forward("WARDSync", {})
    assert name == "Failure"
    failure = protobuf.dict_to_proto(messages.Failure, body)
    assert failure.code == messages.FailureType.ActionCancelled
    assert failure.message == "User declined rollback"
