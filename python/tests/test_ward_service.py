"""The dedicated service adapter cannot forward general device commands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trezorlib import messages
from trezorlib.transport import Timeout
from trezorlib.ward_service import WardService


class Transport:
    def open(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_announcement_can_retry_across_wallet_loop_restart() -> None:
    service = WardService(Transport(), None)
    written = []
    service.write = written.append
    attempts = 0

    def read(timeout: float | None = None) -> messages.WARDServiceOpenAck:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise Timeout("wallet loop restarted")
        return messages.WARDServiceOpenAck(protocol_version=1, buffer_size=64)

    service.read = read
    service.open()
    assert service.bound
    assert attempts == 2
    assert all(isinstance(item, messages.WARDServiceOpen) for item in written)


class MaliciousBackend:
    def call(
        self,
        method: str,
        params: dict | None = None,
        device: Callable[[str, dict], tuple[str, dict]] | None = None,
    ) -> Any:
        assert device is not None
        return device("WipeDevice", {})


def test_service_sync_rejects_management_calls_without_forwarding_them() -> None:
    service = WardService(Transport(), MaliciousBackend())
    service.read = lambda timeout=None: messages.WARDSyncAck(
        nonce=bytes(32),
        version=2,
        counter=0,
        root_known=True,
    )
    written = []
    service.write = written.append
    service.serve_one()
    assert len(written) == 1
    assert isinstance(written[0], messages.Failure)
    assert written[0].message == "WARD backend unavailable"


def test_service_publication_rejects_unrelated_ward_operations() -> None:
    class Backend:
        def call(
            self,
            method: str,
            params: dict | None = None,
            device: Callable[[str, dict], tuple[str, dict]] | None = None,
        ) -> Any:
            assert device is not None
            return device("WARDDiscardPending", {})

    service = WardService(Transport(), Backend())
    service.read = lambda timeout=None: messages.WARDPerformBatchAck(
        counter=1,
        head_mac=bytes(32),
        auth_commit=bytes(32),
    )
    written = []
    service.write = written.append
    service.serve_one()
    assert [type(item) for item in written] == [messages.Failure]


def test_backend_details_are_not_returned_to_the_wallet() -> None:
    class Backend:
        def call(
            self,
            method: str,
            params: dict | None = None,
            device: Callable[[str, dict], tuple[str, dict]] | None = None,
        ) -> Any:
            raise RuntimeError("replica detail that must remain local")

    service = WardService(Transport(), Backend())
    service.read = lambda timeout=None: messages.WARDProofRequest(entry_key=bytes(32))
    written = []
    service.write = written.append
    service.serve_one()
    assert written[0].message == "WARD backend unavailable"


def test_native_daemon_selector_preserves_the_emulator_wallet_port() -> None:
    from trezorlib.transport.udp import UdpTransport
    from trezorlib.ward_service import ward_service_selector

    assert (
        ward_service_selector(UdpTransport("127.0.0.1:37904")) == "udp:127.0.0.1:37904"
    )


def test_native_daemon_selects_the_same_usb_device_by_serial() -> None:
    from trezorlib.transport.webusb import WebUsbTransport
    from trezorlib.ward_service import ward_service_selector

    class Device:
        def getSerialNumber(self) -> str:
            return "test-hardware-serial"

    # A trezorlib webusb:BUS:PORT path is not a native wardd selector.
    # The serial selects the same device while leaving the wallet interface owned by the app.
    wire = WebUsbTransport(Device())
    assert ward_service_selector(wire) == "usb:test-hardware-serial"
    assert wire.handle is None
