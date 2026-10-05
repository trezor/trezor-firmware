"""Load the test app and call its blocks."""

from __future__ import annotations

import io
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

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
    m.ConfirmAction,
    m.ConfirmValue,
    m.ConfirmData,
    m.ConfirmProperties,
    m.ConfirmSummary,
    m.ShowNotice,
)


@dataclass(frozen=True)
class UiResult:
    """The block's answer, exactly as the library returned it."""

    reply: m.Reply
    choice: Optional[int] = None

    def __str__(self) -> str:
        if self.reply == m.Reply.Choice:
            return f"Choice({self.choice})"
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


def props(pairs: Iterable[tuple[str, str]], mono: bool = False) -> list[m.Property]:
    """Properties from (key, value) pairs."""
    return [m.Property(key=k, value=v, mono=mono) for k, v in pairs]


def extras(items: Iterable[tuple[str, Iterable[tuple[str, str]]]]) -> list[m.ExtraItem]:
    """Extras from (label, [(key, value), ...]) pairs."""
    return [m.ExtraItem(label=label, props=props(pairs)) for label, pairs in items]


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

        A forced reload makes sure the build on disk is what runs, rather
        than an image the device kept from before.
        """
        # The most recent build, whichever model it was for.
        image = max(
            artifacts.glob("testapp.trezor.io-*.bin"), key=lambda p: p.stat().st_mtime
        )
        instance_id = extapp.load(
            session,
            image.read_bytes(),
            image.with_suffix(".proof").read_bytes(),
            (artifacts / "rootpacket_0-timestamped-signed.tmr").read_bytes(),
            None,
            force_reload=force_reload,
        )
        return cls(session, instance_id)

    def call(
        self, request: protobuf.MessageType, timeout: Optional[float] = None
    ) -> UiResult:
        """Run one block and return its answer.

        A block that fails answers with a `Failure`, which raises
        `trezorlib.exceptions.TrezorFailure`.
        """
        if not isinstance(request, REQUESTS):
            raise TypeError(f"Not a test app request: {type(request).__name__}")
        return _result(self._exchange(request, timeout))

    @contextmanager
    def progress(self, label: str, total: Optional[int] = None) -> Iterator[Progress]:
        """Show a progress on the device for as long as the `with` block runs.

        `total` is in whatever unit the caller counts; without it the
        progress is indeterminate. The progress ends when the block does,
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


def _expect(resp: ExtAppResponse, message_type: m.MessageType) -> None:
    if resp.message_id != int(message_type):
        raise RuntimeError(f"Unexpected response id {resp.message_id}")


def _result(resp: ExtAppResponse) -> UiResult:
    _expect(resp, m.MessageType.UiResult)
    result = protobuf.load_message(io.BytesIO(resp.data), m.UiResult)
    return UiResult(reply=m.Reply(result.reply), choice=result.choice)
