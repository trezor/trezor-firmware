import utime
from typing import TYPE_CHECKING

import trezornfc as nfc
from trezor import TR, io, log, loop, utils
from trezor.ui import Layout, ProgressLayout

from .crypto import get_trezor_static_key_pair

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Callable, Iterator
    from typing import Any

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
    """Return estimate of upper bound of the duration of N operations in ms."""
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
            progress.report(value, TR.progress__please_wait)

    return callback


async def progress_task(progress_cb: ProgressCallback | None) -> None:
    if not progress_cb:
        return
    s = loop.sleep(40)
    while True:
        await s
        progress_cb()


def is_retryable(exc: Exception) -> str | None:
    if isinstance(exc, EOFError):
        return "Tag disconnected"
    if isinstance(exc, OSError):
        return f"OSError({exc.args})"
    return None


class K1N1Context:
    def __enter__(self) -> Self:
        self.pin: str | None = None
        self.secure_channel = False
        self.conn: nfc.TagConnection | None = None
        log.debug(__name__, "K1N1 exchange start")
        nfc.start_discovery()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        log.debug(__name__, "K1N1 exchange done")
        nfc.stop_discovery()
        if self.conn is not None:
            self.conn.__del__()
            self.conn = None
        self.pin = None

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
            log.warning(__name__, "K1N1 certificate verification not implemented.")
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
        """Wait for K1N1 connection notification."""
        if not nfc.is_connected():  # do not hang if we missed the event
            await self._wait_for_event(io.NFC_CONNECTED)
        self.conn = nfc.connect()
        log.debug(__name__, "Connected to %s", utils.hexlify_if_bytes(self.conn.uid()))

    async def read_share(
        self, progress_cb: ProgressCallback | None = None
    ) -> bytes | None:
        await self._ensure_secure_channel(progress_cb)
        try:
            val = await self._command(nfc.READ_SEED, None, progress_cb)
            if val is not None:
                return _decode_share(val)
            return None
        except nfc.NfcCommandFailed as e:
            # APIv2 returns CommandInternalError if there's no seed
            if e.args[0] == 0xF104:
                return None
            raise

    async def write_share(
        self, value: AnyBytes, progress_cb: ProgressCallback | None = None
    ) -> None:
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
        """Show a layout waiting for K1N1 connection, allowing cancellation."""

        from trezor import TR
        from trezor.ui.layouts.menu import Menu, cancel_leaf, confirm_with_menu
        from trezorui_api import show_info

        self.pin = pin
        self_ctx: K1N1Context = self

        class _Connect(Layout):
            def create_tasks(self) -> Iterator[loop.Task[None]]:
                from trezor.ui import Shutdown
                from trezorui_api import CONFIRMED

                async def _task() -> None:
                    await self_ctx.connect()  # blocks until K1N1 is connected.
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


ctx = K1N1Context()
