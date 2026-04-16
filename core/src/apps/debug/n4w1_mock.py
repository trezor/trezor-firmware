from typing import TYPE_CHECKING

from trezor import log, loop
from trezor.messages import DebugLinkN4W1Read, DebugLinkN4W1Response, DebugLinkN4W1Write
from trezor.ui import Layout

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Awaitable, Iterator

    from trezor.wire.context import Context
    from typing_extensions import Self

    DebugLinkN4W1Request = DebugLinkN4W1Read | DebugLinkN4W1Write


class N4W1Context:
    def __init__(self) -> None:
        self.tx: loop.mailbox[DebugLinkN4W1Request | None] = loop.mailbox()
        self.rx: loop.mailbox[DebugLinkN4W1Response] = loop.mailbox()

    # Invoked by the application (to communicate via N4W1)

    def __enter__(self) -> Self:
        log.debug(__name__, "N4W1 exchange start")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        log.debug(__name__, "N4W1 exchange done")
        self.tx.put(None)

    async def connect(self) -> None:
        """Wait for N4W1 connection notification."""
        res = await self.rx
        assert res.value is None

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

    # Invoked to communicate with N4W1 emulator over apps.debug.DEBUG_CONTEXT

    async def handle(self, ctx: Context) -> None:
        """Called from `apps.debug.dispatch_DebugLinkConnected()`."""
        self.rx.put(DebugLinkN4W1Response(value=None))  # notify `self.connect()`
        while (req := await self.tx) is not None:
            res = await ctx.call(req, DebugLinkN4W1Response)
            self.rx.put(res)

    def confirm_connect(
        self, *, title: str, description: str, button: str, br_name: str | None
    ) -> Awaitable[None]:
        """Show a layout waiting for N4W1 connection, allowing cancellation."""

        from trezor import TR
        from trezor.ui.layouts.menu import Menu, confirm_with_menu
        from trezorui_api import show_info

        self_ctx: N4W1Context = self

        class _Connect(Layout):

            def create_tasks(self) -> Iterator[loop.Task[None]]:
                from trezor.ui import Shutdown
                from trezorui_api import CONFIRMED

                async def _task() -> None:
                    await self_ctx.connect()  # blocks until N4W1 is connected.
                    try:
                        # emitting a message raises Shutdown exception
                        self._emit_message(CONFIRMED)
                    except Shutdown:
                        pass

                yield from super().create_tasks()
                yield _task()

        main = show_info(
            title=title,
            description=description,
            button=(button, False),
            external_menu=True,
        )
        return confirm_with_menu(
            main,
            Menu.root(cancel=TR.buttons__cancel),
            br_name=br_name,
            layout_type=_Connect,
        )


ctx = N4W1Context()
