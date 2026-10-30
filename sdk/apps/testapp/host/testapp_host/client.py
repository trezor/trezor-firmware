"""Load the test app and call its layouts."""

from __future__ import annotations

import io
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from trezorlib import extapp, protobuf
from trezorlib.messages import ExtAppMessage, ExtAppResponse

from . import messages as m

if TYPE_CHECKING:
    from trezorlib.client import Session
    from trezorlib.transport import Transport

REPO = Path(__file__).resolve().parents[5]

# Where `make extapp_build_emu EXTAPP=testapp` puts the build: one
# `<id>-<version>-<lang>-<MODEL>-<target>.{bin,proof}` pair per build, and one
# root packet covering every app built there.
ARTIFACTS = REPO / "sdk" / "apps" / "target" / "artifacts"

# Every request `TestApp.call` sends, by class; the wire id is the MessageType
# of the same name. A progress is not one: it is `TestApp.progress`.
REQUESTS = (
    m.Review,
    m.Danger,
    m.Details,
    m.StreamData,
    m.VerifyAddress,
    m.VerifyPubkey,
    m.Done,
    m.Showcase,
)

# The API reference's examples, by the name `TestApp.showcase` dispatches on.
SHOWCASES = (
    "send",
    "delegate",
    "claim-owner",
    "unknown-contract",
    "path-warning",
    "typed-data",
    "get-address",
    "get-pubkey",
    "contract-data",
    "signing-progress",
)


@dataclass(frozen=True)
class UiResult:
    """How the layout ended: Confirmed, Cancelled or ShowDetails."""

    reply: m.Reply

    def __str__(self) -> str:
        return self.reply.name


def connect(
    transport: Optional["Transport"] = None, app_name: str = "testapp"
) -> "Session":
    """Open a standard session on the first device found (the emulator).

    Pairs over THP where the device needs it; may show one pairing screen.
    """
    from trezorlib import transport as transport_module
    from trezorlib.client import get_default_client

    if transport is None:
        # The emulator answers a single short ping, which it can miss while
        # still busy with the previous request, so a miss is retried.
        deadline = time.monotonic() + 5
        while not (devices := transport_module.enumerate_devices()):
            if time.monotonic() > deadline:
                raise RuntimeError("No Trezor found; start the emulator first.")
            time.sleep(0.2)
        transport = devices[0]
    return get_default_client(app_name, transport).get_session()


def field(
    kind: m.FieldKind, value: Union[str, bytes], label: Optional[str] = None
) -> m.Field:
    """One fact: what it is, its value, and a label unless it is a note or
    warning. A string value is UTF-8 on the wire."""
    if isinstance(value, str):
        value = value.encode()
    return m.Field(kind=kind, label=label, value=value)


def text(label: str, value: str) -> m.Field:
    """Words or a number, shown as written."""
    return field(m.FieldKind.Text, value, label)


def amount(label: str, value: str) -> m.Field:
    """A sum with its unit, already formatted by the app."""
    return field(m.FieldKind.Amount, value, label)


def address(label: str, value: str) -> m.Field:
    """Something compared character by character."""
    return field(m.FieldKind.Address, value, label)


def data(label: str, value: bytes) -> m.Field:
    """Raw bytes, shown as hex and paged."""
    return field(m.FieldKind.Data, value, label)


def note(value: str) -> m.Field:
    """A sentence with no label."""
    return field(m.FieldKind.Note, value)


def warning(value: str) -> m.Field:
    """A sentence to weigh before confirming."""
    return field(m.FieldKind.Warning, value)


def extras(*items: tuple[str, Iterable[m.Field]]) -> list[m.Extra]:
    """Extras from (label, fields) pairs."""
    return [m.Extra(label=label, fields=list(fields)) for label, fields in items]


class TestApp:
    """The loaded test app on one session."""

    def __init__(self, session: "Session", instance_id: int) -> None:
        self.session = session
        self.instance_id = instance_id

    @classmethod
    def load(
        cls,
        session: "Session",
        artifacts: Path = ARTIFACTS,
        force_reload: bool = True,
    ) -> "TestApp":
        """Load the app from `artifacts`.

        Picks the image built for the connected device: its model, and the
        emulator's or the hardware's architecture. A forced reload makes sure
        the build on disk is what runs, rather than an image the device kept
        from before.
        """
        from trezorlib.transport.udp import UdpTransport

        model = session.client.features.internal_model
        emulator = isinstance(session.client.transport, UdpTransport)
        arch = "linux-x86_64" if emulator else "armv8m"
        images = (artifacts / "serialized").glob(
            f"testapp.trezor.io/*/*_{arch}_*_{model}_*.tapp"
        )
        tapp = max(images, key=lambda p: p.stat().st_mtime, default=None)
        if tapp is None:
            raise FileNotFoundError(f"No testapp build for {model} ({arch})")
        instance_id = extapp.load_tapp(session, tapp, match_fingerprint=force_reload)
        return cls(session, instance_id)

    def call(
        self, request: protobuf.MessageType, timeout: Optional[float] = None
    ) -> UiResult:
        """Run one layout and return its answer.

        A layout that fails answers with a `Failure`, which raises
        `trezorlib.exceptions.TrezorFailure`.
        """
        if not isinstance(request, REQUESTS):
            raise TypeError(f"Not a test app request: {type(request).__name__}")
        return _result(self._exchange(request, timeout))

    def showcase(self, name: str, timeout: Optional[float] = None) -> UiResult:
        """Run one flow from the API reference's examples, by name."""
        if name not in SHOWCASES:
            raise ValueError(f"Unknown showcase: {name}")
        return self.call(m.Showcase(name=name), timeout)

    @contextmanager
    def progress(self, label: str, total: Optional[int] = None) -> Iterator[Progress]:
        """Show a progress on the device for as long as the `with` layout runs.

        `total` is in whatever unit the caller counts; without it the
        progress is indeterminate. The progress ends when the layout does,
        however it ends:

            with app.progress("Working...", total=len(chunks)) as p:
                for chunk in chunks:
                    process(chunk)
                    p.step()
        """
        _expect(
            self._exchange(m.ShowProgress(label=label, total=total)),
            m.MessageType.ProgressTick,
        )
        try:
            yield Progress(self)
        finally:
            _result(self._exchange(m.ProgressEnd()))

    def _exchange(
        self, message: protobuf.MessageType, timeout: Optional[float] = None
    ) -> ExtAppResponse:
        """Send one message to the app and return its next message."""
        buf = io.BytesIO()
        protobuf.dump_message(buf, message)
        msg = ExtAppMessage(
            instance_id=self.instance_id,
            message_id=int(m.MessageType[type(message).__name__]),
            data=buf.getvalue(),
        )
        with self.session:
            return self.session.client._call(
                self.session, msg, expect=ExtAppResponse, timeout=timeout
            )


class Progress:
    """A running progress; see `TestApp.progress`."""

    def __init__(self, app: TestApp) -> None:
        self._app = app

    def step(self, units: int = 1) -> None:
        """Report `units` more units of work done."""
        _expect(
            self._app._exchange(m.ProgressStep(units=units)), m.MessageType.ProgressTick
        )

    def label(self, text: str) -> None:
        """Change the text under the bar."""
        _expect(
            self._app._exchange(m.ProgressLabel(label=text)),
            m.MessageType.ProgressTick,
        )


def _expect(resp: ExtAppResponse, message_type: m.MessageType) -> None:
    if resp.message_id != int(message_type):
        raise RuntimeError(f"Unexpected response id {resp.message_id}")


def _result(resp: ExtAppResponse) -> UiResult:
    _expect(resp, m.MessageType.UiResult)
    result = protobuf.load_message(io.BytesIO(resp.data), m.UiResult)
    return UiResult(reply=m.Reply(result.reply))
