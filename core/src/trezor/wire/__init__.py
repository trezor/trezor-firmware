"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec/codec_v1.py` or `trezor/wire/thp/context.py`.
- Transferred over USB interface, or UDP in case of Unix emulation.

This module:

1. Runs workflows, also called `handlers`, to process the message.
2. Creates and passes the `Context` object to the handlers. This provides an interface to
   wait, read, write etc. on the wire.

## Session handler

When the `wire.setup` is called the `handle_session` coroutine is scheduled. The
`handle_session` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known the first handler is called. This way the
`handle_session` goes through all the workflows.

"""

from typing import TYPE_CHECKING

from trezor import loop, protobuf, utils

from .. import workflow
from . import message_handler, protocol_common

if utils.USE_THP:
    from .thp import received_message_handler
    from .thp.interface_context import ThpContext
else:
    from .codec.codec_context import CodecContext

from .context import UnexpectedMessageException
from .message_handler import failure

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from .errors import *  # isort:skip # noqa: F401,F403

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from types import TracebackType
    from typing import Any, Callable, Coroutine, Generic, Type, TypeVar

    from trezor.wire.thp.channel import Channel

    T = TypeVar("T")
    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[[Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)
else:
    Generic = (object,)
    T = 0


class _HighSpeed:
    def __enter__(self) -> "_HighSpeed":
        if utils.USE_BLE:
            from trezorble import set_high_speed

            set_high_speed(True)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if utils.USE_BLE:
            from trezorble import set_high_speed

            set_high_speed(False)
        return False


high_speed: "_HighSpeed" = _HighSpeed()


class Provider(Generic[T]):
    def __init__(self, obj: T) -> None:
        self.obj = obj

    def take(self) -> T | None:
        if self.obj is None:
            return None

        obj = self.obj
        self.obj = None
        return obj


if utils.USE_THP:
    from .thp.memory_manager import ThpBuffer

    # Allocate THP read/write buffers in more stable area of memory
    THP_BUFFERS_PROVIDER = Provider((ThpBuffer(), ThpBuffer()))

    if __debug__:
        _THP_CHANNELS = []

        def find_thp_channel(channel_id: AnyBytes) -> Channel | None:
            """Used by `DebugLinkGetPairingInfo` (only for tests)."""
            key = int.from_bytes(channel_id, "big")
            for channels in _THP_CHANNELS:
                result = channels.get(key)
                if result is not None:
                    return result
            return None

    def setup(*ifaces: WireInterface) -> None:
        """Initialize the wire stack on the provided interfaces."""
        loop.schedule(handle_session_thp(*ifaces))

    async def handle_session_thp(*ifaces: WireInterface) -> None:
        ctx = ThpContext(*ifaces)
        if __debug__:
            _THP_CHANNELS.extend(iface_ctx._channels for iface_ctx in ctx._iface_ctxs)

        try:
            while (channel := await ctx.get_next_message()) is None:
                # wait until a new channel is established (on any interface)
                pass

            while await received_message_handler.handle_received_message(channel):
                pass
        finally:
            if __debug__:
                log.debug(__name__, "Finished THP session: %s", ifaces)
            # Wait for all active workflows to finish.
            await workflow.join_all()
            if __debug__:
                import apps.debug

                await apps.debug.close_session()
            loop.clear()

else:

    # Reallocated once per session and shared between all wire interfaces.
    # Acquired by the first call to `CodecContext.read_from_wire()`.
    WIRE_BUFFER_PROVIDER = Provider(bytearray(8192))

    def setup(*ifaces: WireInterface) -> None:
        """Initialize the wire stack on the provided interfaces."""
        for iface in ifaces:
            loop.schedule(handle_session_codec(iface))

    async def handle_session_codec(iface: WireInterface) -> None:
        ctx = CodecContext(iface, WIRE_BUFFER_PROVIDER)
        next_msg: protocol_common.Message | None = None

        # Take a mark of modules that are imported at this point, so we can
        # roll back and un-import any others.
        modules = utils.unimport_begin()
        while True:
            try:
                if next_msg is None:
                    # If the previous run did not keep an unprocessed message for us,
                    # wait for a new one coming from the wire.
                    try:
                        msg = await ctx.read_from_wire()
                    except protocol_common.WireError as exc:
                        if __debug__:
                            log.exception(__name__, exc, iface=iface)
                        await ctx.write(failure(exc))
                        continue
                else:
                    # Process the message from previous run.
                    msg = next_msg
                    next_msg = None

                do_not_restart = False
                try:
                    do_not_restart = await message_handler.handle_single_message(
                        ctx, msg
                    )
                except UnexpectedMessageException as unexpected:
                    # The workflow was interrupted by an unexpected message. We need to
                    # process it as if it was a new message...
                    next_msg = unexpected.msg
                    # ...and we must not restart because that would lose the message.
                    do_not_restart = True
                    continue
                except Exception as exc:
                    # Log and ignore. The session handler can only exit explicitly in the
                    # following finally block.
                    if __debug__:
                        log.exception(__name__, exc, iface=iface)
                finally:
                    # Unload modules imported by the workflow. Should not raise.
                    utils.unimport_end(modules)

                    if not do_not_restart:
                        # Wait for all active workflows to finish.
                        await workflow.join_all()
                        if __debug__:
                            import apps.debug

                            await apps.debug.close_session()
                        # Let the session be restarted from `main`.
                        loop.clear()
                        return  # pylint: disable=lost-exception

            except Exception as exc:
                # Log and try again. The session handler can only exit explicitly via
                # loop.clear() above.
                if __debug__:
                    log.exception(__name__, exc, iface=iface)
