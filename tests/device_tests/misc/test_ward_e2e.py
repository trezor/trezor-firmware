"""The single-device end-to-end flows of tools/ward_stack.py, as device tests.

ward_stack.py drives rust/ward-relay/examples/trezor_hwi.py through the default write and
lookup, and --long (ten entries, each label checked on the device), over the wallet relay
or, with --service-channel, over the WARD service interface. These tests run the same
flows on the device under test, hardware included, against a real HTTP WARD Manager as
the stack does. --extra_long is left to the stack: it takes too long for these suites.
"""

from __future__ import annotations

import subprocess
import typing as t
from pathlib import Path

import pytest

from trezorlib.debuglink import DebugSession as Session
from trezorlib.ward_relay import WardAdapter, WardBackend

from . import test_ward_relay as relay_helpers
from .test_ward_relay import APP, NETWORK, SUITE_DIR, _confirmed
from .test_ward_service_channel import start_native_wardd

wardd = relay_helpers.wardd
wardd_port = relay_helpers.wardd_port
wm_url = relay_helpers.wm_url

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.skipif(not SUITE_DIR, reason="WARDD_SUITE_DIR is not set"),
    pytest.mark.parametrize("wm_url", ["http"], indirect=True),
]

# trezor_hwi.py's defaults, as ward_stack.py runs it.
ADDRESS = "bc1qwarddemo"
LABEL = "WARD demo"
LONG_ENTRIES = 10


@pytest.fixture(params=["wallet-relay", "service"])
def backend(
    request: pytest.FixtureRequest,
    session: Session,
    wardd_port: int,
    wm_url: str | None,
    tmp_path: Path,
) -> t.Iterator[WardBackend]:
    """wardd answering the device: over the wallet relay, or on the service interface."""
    if request.param == "wallet-relay":
        yield request.getfixturevalue("wardd")
        return

    from trezorlib.ward_wallet import WardWalletClient

    process, _ = start_native_wardd(session, wardd_port, wm_url, tmp_path)
    output = ""
    try:
        assert process.stdout is not None
        output = process.stdout.readline()
        assert "service connected" in output, output
        with WardWalletClient() as client:
            yield client
    finally:
        process.terminate()
        try:
            rest, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            rest, _ = process.communicate(timeout=5)
        (tmp_path / "wardd-native.log").write_text(output + rest)


def _write(session: Session, backend: WardBackend, address: str, label: str) -> dict:
    result = _confirmed(
        session,
        lambda current: WardAdapter(current, backend).update(
            APP, address, NETWORK, {"label": label}
        ),
    )
    assert not result.get("conflict") and not result.get("localCacheError"), result
    return result


def _display(session: Session, backend: WardBackend, address: str, label: str) -> None:
    _confirmed(
        session,
        lambda current: WardAdapter(current, backend).display_address(APP, address),
        expected_text=label,
    )


def test_ward_stack_default(session: Session, backend: WardBackend) -> None:
    adapter = WardAdapter(session, backend)
    assert adapter.sync()["counter"] == 0
    assert _write(session, backend, ADDRESS, LABEL)["counter"] == 1
    found = adapter.lookup(APP, ADDRESS, NETWORK)
    assert found["valid"] and found["isMember"], found


def test_ward_stack_long(session: Session, backend: WardBackend) -> None:
    adapter = WardAdapter(session, backend)
    assert adapter.sync()["counter"] == 0
    entries = [
        (
            ADDRESS if index == 0 else f"{ADDRESS}-{index + 1:02d}",
            f"{LABEL} {index + 1:02d}",
        )
        for index in range(LONG_ENTRIES)
    ]
    for counter, (address, label) in enumerate(entries, 1):
        assert _write(session, backend, address, label)["counter"] == counter
    for address, label in entries:
        found = adapter.lookup(APP, address, NETWORK)
        assert found["valid"] and found["isMember"], found
        _display(session, backend, address, label)
