"""Dedicated codec-v1 WARD backend; the wallet transport remains owned by its app.

The device reads these messages one USB report at a time. Host-side protobuf
encoding is unchanged. This adapter forwards only sync/finalization calls from
wardd; keys, prompts and unrelated device commands never use this interface.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from . import mapping, messages, protobuf, protocol_v1
from .transport import Timeout, Transport
from .transport.udp import UdpTransport
from .ward_relay import WarddClient

WARD_PORT_OFFSET = 7
WARD_USB_SUBCLASS = 0x57
WARD_USB_PROTOCOL = 0x01


def ward_transport(wire: Transport) -> Transport:
    if isinstance(wire, UdpTransport):
        host, port = wire.device
        return UdpTransport(f"{host}:{port + WARD_PORT_OFFSET}")
    from .transport.webusb import WebUsbTransport

    if not isinstance(wire, WebUsbTransport):
        raise ValueError("WARD service requires USB or emulator UDP")
    ward = WebUsbTransport(wire.device)
    for configuration in wire.device.iterConfigurations():
        for interface in configuration.iterInterfaces():
            for setting in interface.iterSettings():
                if (
                    setting.getSubClass() != WARD_USB_SUBCLASS
                    or setting.getProtocol() != WARD_USB_PROTOCOL
                ):
                    continue
                for endpoint in setting.iterEndpoints():
                    address = endpoint.getAddress()
                    if address & 0x80:
                        ward.interface = setting.getNumber()
                        ward.endpoint = address & 0x7F
                        return ward
    raise ValueError("device has no WARD service interface")


class WardService:
    def __init__(self, transport: Transport, backend: WarddClient) -> None:
        self.transport = transport
        self.backend = backend
        self.mapping = mapping.DEFAULT_MAPPING
        self.bound = False
        self.served: list[str] = []
        self.errors: list[BaseException] = []

    def write(self, message: protobuf.MessageType) -> None:
        kind, payload = self.mapping.encode(message)
        protocol_v1.write(self.transport, kind, payload)

    def read(self, timeout: float | None = None) -> protobuf.MessageType:
        kind, payload = protocol_v1.read(self.transport, timeout=timeout)
        return self.mapping.decode(kind, payload)

    def open(self) -> None:
        self.transport.open()
        try:
            # Codec-v1 wallets restart their event loop after a workflow. An
            # announcement arriving at that boundary can lose its acknowledgement.
            # Opening is idempotent; application exchanges are never retried here.
            for attempt in range(3):
                self.write(messages.WARDServiceOpen(protocol_version=1))
                try:
                    ack = self.read(timeout=1)
                    break
                except Timeout:
                    if attempt == 2:
                        raise
            if (
                not isinstance(ack, messages.WARDServiceOpenAck)
                or ack.protocol_version != 1
                or ack.buffer_size != 64
            ):
                raise ValueError("unsupported WARD service interface")
            self.bound = True
        except BaseException:
            self.transport.close()
            raise

    def close(self) -> None:
        if self.bound:
            try:
                self.write(messages.WARDServiceOpen(protocol_version=1, close=True))
                self.read(timeout=1)
            except Exception:
                pass
            self.bound = False
        self.transport.close()

    def _device(
        self, allowed: frozenset[str]
    ) -> Callable[[str, dict], tuple[str, dict]]:
        def call(name: str, body: dict) -> tuple[str, dict]:
            if name not in allowed:
                raise ValueError("wardd requested a forbidden service operation")
            definition = getattr(messages, name)
            self.write(protobuf.dict_to_proto(definition, body))
            reply = self.read(timeout=35)
            return type(reply).__name__, protobuf.to_dict(reply)

        return call

    def serve_one(self, timeout: float | None = None) -> str:
        request = self.read(timeout)
        name = type(request).__name__
        body = protobuf.to_dict(request)
        try:
            if isinstance(request, messages.WARDSyncAck):
                self.backend.call(
                    "serviceSync",
                    {"initialAck": body},
                    self._device(
                        frozenset(
                            (
                                "WARDIngestAttestation",
                                "WARDVerifyChain",
                                "WARDReconcile",
                            )
                        )
                    ),
                )
                reply = messages.WARDServiceDone()
            elif isinstance(request, messages.WARDProofRequest):
                answer = self.backend.call("answerProofRequest", {"request": body})
                reply = protobuf.dict_to_proto(messages.WARDProofAck, answer)
            elif isinstance(request, messages.WARDNodeRequest):
                answer = self.backend.call(
                    "answerNodeRequest", {"request": body, "maxNodes": 1}
                )
                reply = protobuf.dict_to_proto(messages.WARDNodeAck, answer)
            elif isinstance(
                request, (messages.WARDPerformBatchAck, messages.WARDPerformRevertAck)
            ):
                revert = isinstance(request, messages.WARDPerformRevertAck)
                self.backend.call(
                    "servicePublish",
                    {"candidate": body, "kind": "revert" if revert else "commit"},
                    self._device(
                        frozenset(
                            (
                                "WARDConfirmRevertByWM"
                                if revert
                                else "WARDConfirmBatchByWM",
                            )
                        )
                    ),
                )
                reply = messages.WARDServiceDone()
            else:
                raise ValueError("unexpected device service request")
        except Exception:
            # Backend details may contain replica data. Keep them off the wallet and logs.
            reply = messages.Failure(
                code=messages.FailureType.DataError, message="WARD backend unavailable"
            )
        self.write(reply)
        self.served.append(name)
        return name

    @contextmanager
    def serving(self) -> Iterator[WardService]:
        stop = threading.Event()

        def run() -> None:
            while not stop.is_set():
                try:
                    self.serve_one(timeout=0.1)
                except Timeout:
                    continue
                except BaseException as exc:
                    self.errors.append(exc)
                    return

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        try:
            yield self
        finally:
            stop.set()
            worker.join(timeout=40)
            if worker.is_alive():
                raise RuntimeError("WARD service worker did not stop")
            if self.errors:
                raise self.errors[0]
