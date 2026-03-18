from typing import TYPE_CHECKING

from trezor import log, loop
from trezor.messages import DebugLinkN4W1Read, DebugLinkN4W1Response, DebugLinkN4W1Write

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any

    from trezor.wire.context import Context
    from typing_extensions import Self

    DebugLinkN4W1Request = DebugLinkN4W1Read | DebugLinkN4W1Write


class N4W1Context:
    def __init__(self) -> None:
        self.tx: loop.mailbox[DebugLinkN4W1Request | None] = loop.mailbox()
        self.rx: loop.mailbox[DebugLinkN4W1Response] = loop.mailbox()

    def __enter__(self) -> Self:
        log.debug(__name__, "N4W1 exchange start")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        log.debug(__name__, "N4W1 exchange done")
        self.tx.put(None)

    async def read(self, key: str) -> AnyBytes | None:
        """Read a specific entry from N4W1."""
        log.debug(__name__, "N4W1 read: %s", key)
        self.tx.put(DebugLinkN4W1Read(key=key))
        # blocks until N4W1 connection + response
        resp = await self.rx
        log.debug(__name__, "N4W1 response: %s", resp.value)
        return resp.value

    async def write(self, key: str, value: AnyBytes | None) -> AnyBytes | None:
        """Write/delete a specific entry from N4W1."""
        log.debug(__name__, "N4W1 write: %s %s", key, value)
        self.tx.put(DebugLinkN4W1Write(key=key, value=value))
        # blocks until N4W1 connection + response
        resp = await self.rx
        log.debug(__name__, "N4W1 response: %s", resp.value)
        return resp.value

    async def handle(self, ctx: Context) -> None:
        """Called from `dispatch_DebugLinkConnected`."""
        while (req := await self.tx) is not None:
            res = await ctx.call(req, DebugLinkN4W1Response)
            self.rx.put(res)


ctx = N4W1Context()
