from typing import TYPE_CHECKING

from trezor import log, loop
from trezor.messages import DebugLinkNfcRead, DebugLinkNfcResponse, DebugLinkNfcWrite

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any

    from trezor.wire.context import Context
    from typing_extensions import Self

    DebugLinkNfcRequest = DebugLinkNfcRead | DebugLinkNfcWrite


class NfcContext:
    def __init__(self) -> None:
        self.tx: loop.mailbox[DebugLinkNfcRequest | None] = loop.mailbox()
        self.rx: loop.mailbox[DebugLinkNfcResponse] = loop.mailbox()

    def __enter__(self) -> Self:
        log.debug(__name__, "NFC exchange start")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        log.debug(__name__, "NFC exchange done")
        self.tx.put(None)

    async def read(self, key: str) -> AnyBytes | None:
        """Read a specific entry from NFC card."""
        log.debug(__name__, "NFC read: %s", key)
        self.tx.put(DebugLinkNfcRead(key=key))
        # blocks until NFC connection + response
        resp = await self.rx
        log.debug(__name__, "NFC response: %s", resp.value)
        return resp.value

    async def write(self, key: str, value: AnyBytes | None) -> AnyBytes | None:
        """Write/delete a specific entry from NFC card."""
        log.debug(__name__, "NFC write: %s %s", key, value)
        self.tx.put(DebugLinkNfcWrite(key=key, value=value))
        # blocks until NFC connection + response
        resp = await self.rx
        log.debug(__name__, "NFC response: %s", resp.value)
        return resp.value

    async def handle(self, ctx: Context) -> None:
        """Called from `dispatch_DebugLinkConnected`."""
        while (req := await self.tx) is not None:
            res = await ctx.call(req, DebugLinkNfcResponse)
            self.rx.put(res)


ctx = NfcContext()
