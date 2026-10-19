import utime
from typing import TYPE_CHECKING

import trezornfc as nfc
from trezor import io, log, loop, utils
from trezor.ui import Layout, ProgressLayout

from .crypto import get_trezor_static_key_pair

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Callable, Iterator
    from typing import Any

    from trezor.wire.context import Context
    from typing_extensions import Self

    ProgressCallback = Callable[[], None]


def _encode_share(val: AnyBytes, length: int = 256) -> bytes:
    size = len(val)
    if size > length:
        raise ValueError("Share too long")
    return bytes(val) + (b"\x00" * (length - size))


def _decode_share(val: bytes) -> bytes:
    return val.rstrip(b"\x00")


def op_duration(n_ops: int = 1, handshake: bool = True) -> int:
    return int(handshake) * 1800 + (n_ops * 130)


def time_based_progress(
    progress: ProgressLayout, duration_ms: int = op_duration()
) -> ProgressCallback:
    # TODO don't redraw too often
    started = utime.ticks_ms()

    def callback() -> None:
        elapsed = utime.ticks_diff(utime.ticks_ms(), started)
        value = elapsed * 1000 // duration_ms
        if value <= 1000:
            log.debug(__name__, f"progress({value})")
            progress.report(value, "Wait")

    return callback


async def progress_task(progress_cb: ProgressCallback | None) -> None:
    if not progress_cb:
        return
    s = loop.sleep(40)
    while True:
        await s
        progress_cb()


def is_retryable(exc: Exception) -> str | None:
    if isinstance(exc, nfc.NfcCommandFailed) and exc.args[0] in (0x0000, 0x1337):
        return "Driver error"
    if isinstance(exc, EOFError):
        return "Tag disconnected"
    if isinstance(exc, OSError):
        # TODO: restrict to EINVAL?
        return f"OSError ({exc.args})"
    return None


class N1W1Context:
    def __enter__(self) -> Self:
        # TODO clear uid, context
        self.pin: str | None = None
        self.secure_channel = False
        self.conn: nfc.TagConnection | None = None
        log.debug(__name__, "N1W1 exchange start")
        nfc.start_discovery()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        # TODO clear uid, context
        log.debug(__name__, "N1W1 exchange done")
        nfc.stop_discovery()

    async def _wait_for_event(
        self, awaited_event: int, progress_cb: ProgressCallback | None = None
    ) -> None:
        nfc = loop.wait(io.NFC_EVENT)
        pt = loop.spawn(progress_task(progress_cb))
        try:
            while True:
                event = await nfc
                if __debug__:
                    log.debug(__name__, "NFC event: %s", event)
                if event == awaited_event:
                    return
        finally:
            pt.close()

    async def _ensure_secure_channel(
        self, progress_cb: ProgressCallback | None = None
    ) -> None:
        assert self.conn is not None
        if self.secure_channel:
            return

        def verify_cert(static_public_key: AnyBytes, cert: AnyBytes) -> bool:
            if __debug__:
                log.info(
                    __name__, "Card key: %s", utils.hexlify_if_bytes(static_public_key)
                )
                log.info(__name__, "Card cert: %s", utils.hexlify_if_bytes(cert))
            return True

        static_private_key, static_public_key = get_trezor_static_key_pair()
        while not self.conn.setup(
            static_private_key, static_public_key, self.pin, verify_cert
        ):
            await self._wait_for_event(io.NFC_TRANSCEIVE_DONE, progress_cb)
        self.secure_channel = True

    async def _command(
        self,
        ins: int,
        data: AnyBytes | None,
        progress_cb: ProgressCallback | None = None,
    ) -> bytes | None:
        assert self.conn is not None
        self.conn.send_command(ins, data)
        await self._wait_for_event(io.NFC_TRANSCEIVE_DONE, progress_cb)
        return self.conn.recv_response()

    async def connect(self) -> None:
        """Wait for N1W1 connection notification."""
        await self._wait_for_event(io.NFC_CONNECTED)
        self.conn = nfc.connect()
        log.debug(__name__, "Connected to %s", utils.hexlify_if_bytes(self.conn.uid()))

    async def read_share(
        self, progress_cb: ProgressCallback | None = None
    ) -> bytes | None:
        """Read a specific entry from N1W1."""
        await self._ensure_secure_channel(progress_cb)
        try:
            val = await self._command(nfc.READ_SEED, None, progress_cb)
            if val is not None:
                return _decode_share(val)
            return None
        except nfc.NfcCommandFailed as e:
            # APIv2 returns CommandInternalError if there's no seed
            if e.args[0] == 0xF104:  # FIXME: seed not found
                return None
            raise

    async def write_share(
        self, value: AnyBytes, progress_cb: ProgressCallback | None = None
    ) -> None:
        """Write/delete a specific entry from N1W1."""
        await self._ensure_secure_channel(progress_cb)
        value = _encode_share(value, 256)
        await self._command(nfc.WRITE_SEED, value, progress_cb)

    async def uid(self, progress_cb: ProgressCallback | None = None) -> bytes:
        """Read card UID as bytes."""
        val = await self._command(nfc.GET_UID, None, progress_cb)
        if val is None or len(val) == 0:
            raise ValueError("Card has no UID")
        return val

    async def confirm_connect(
        self,
        *,
        title: str,
        description: str,
        button: str = "Hold the card to the back of\u00a0the\u00a0Trezor.",
        br_name: str | None,
        pin: str | None = "",
    ) -> None:
        """Show a layout waiting for N1W1 connection, allowing cancellation."""

        from trezor import TR
        from trezor.ui.layouts.menu import Menu, cancel_leaf, confirm_with_menu
        from trezorui_api import show_info

        self.pin = pin
        self_ctx: N1W1Context = self

        class _Connect(Layout):
            def create_tasks(self) -> Iterator[loop.Task[None]]:
                from trezor.ui import Shutdown
                from trezorui_api import CONFIRMED

                async def _task() -> None:
                    await self_ctx.connect()  # blocks until N1W1 is connected.
                    try:
                        # emitting a message raises Shutdown exception
                        self._emit_message(CONFIRMED)
                    except Shutdown:
                        pass

                yield from super().create_tasks()
                yield _task()

        with show_info(
            title=title,
            description=description,
            button=(button, False),
            external_menu=True,
        ) as main:
            return await confirm_with_menu(
                main,
                Menu([cancel_leaf(TR.buttons__cancel)]),  # TODO: troubleshooting
                br_name=br_name,
                layout_type=_Connect,
            )


if utils.EMULATOR:
    from trezor.messages import (
        DebugLinkN1W1Read,
        DebugLinkN1W1Response,
        DebugLinkN1W1Write,
    )

    DebugLinkN1W1Request = DebugLinkN1W1Read | DebugLinkN1W1Write

    class N1W1DebugLinkContext(N1W1Context):
        def __init__(self) -> None:
            super().__init__()
            self.tx: loop.mailbox[DebugLinkN1W1Request | None] = loop.mailbox()
            self.rx: loop.mailbox[DebugLinkN1W1Response] = loop.mailbox()

        def __enter__(self) -> Self:
            log.debug(__name__, "N1W1 exchange start")
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
            log.debug(__name__, "N1W1 exchange done")
            self.tx.put(None)

        async def connect(self) -> None:
            """Wait for N1W1 connection notification."""
            res = await self.rx
            # verify it's connected maybe
            assert res.value is None

        async def read_share(self) -> AnyBytes | None:
            return await self._read_entry(key="mnemonic")

        async def write_share(self, value: AnyBytes | None) -> AnyBytes | None:
            """Write/delete a specific entry from N1W1."""
            return await self._write_entry(key="mnemonic", value=value)

        async def _read_entry(self, key: str) -> AnyBytes | None:
            """Read a specific entry from N1W1."""
            log.debug(__name__, "N1W1 read: %s", key)
            self.tx.put(DebugLinkN1W1Read(key=key))
            # blocks until N1W1 connection + response
            resp = await self.rx
            log.debug(__name__, "N1W1 response: %s", resp.value)
            return resp.value

        async def _write_entry(
            self, key: str, value: AnyBytes | None
        ) -> AnyBytes | None:
            """Write/delete a specific entry from N1W1."""
            log.debug(__name__, "N1W1 write: %s %s", key, value)
            self.tx.put(DebugLinkN1W1Write(key=key, value=value))
            # blocks until N1W1 connection + response
            resp = await self.rx
            log.debug(__name__, "N1W1 response: %s", resp.value)
            return resp.value

        # Invoked to communicate with N1W1 emulator over apps.debug.DEBUG_CONTEXT
        async def handle(self, ctx: Context) -> None:
            """Called from `apps.debug.dispatch_DebugLinkConnected()`."""
            self.rx.put(DebugLinkN1W1Response(value=None))  # notify `self.connect()`
            while (req := await self.tx) is not None:
                res = await ctx.call(req, DebugLinkN1W1Response)
                self.rx.put(res)

    ctx = N1W1DebugLinkContext()
else:
    ctx = N1W1Context()
