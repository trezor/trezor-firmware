"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec_v1.py` or `trezor/wire/thp_v3.py`.
- Transferred over USB interface, or UDP in case of Unix emulation.

This module:

1. Runs workflows, also called `handlers`, to process the message.
2. Creates and passes the `Context` object to the handlers. This provides an interface to
   wait, read, write etc. on the wire.

## Session handler

When the `wire.setup` is called the `handle_session` (or `handle_thp_session`) coroutine is scheduled. The
`handle_session` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known the first handler is called. This way the
`handle_session` goes through all the workflows.

"""

from typing import TYPE_CHECKING

from trezor import log, loop, protobuf, utils
from trezor.wire import context, message_handler, protocol_common, thp_v3
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.message_handler import (
    WIRE_BUFFER,
    WIRE_BUFFER_DEBUG,
    failure,
    find_handler,
)

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403


if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any, Callable, Coroutine, TypeVar

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[[Msg], HandlerTask]
    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


# If set to False protobuf messages marked with "experimental_message" option are rejected.
EXPERIMENTAL_ENABLED = False


def setup(iface: WireInterface, is_debug_session: bool = False) -> None:
    """Initialize the wire stack on passed WireInterface."""
    if utils.USE_THP and not is_debug_session:
        loop.schedule(handle_thp_session(iface, is_debug_session))
    else:
        loop.schedule(handle_session(iface, is_debug_session))


async def handle_thp_session(iface: WireInterface, is_debug_session: bool = False):
    if __debug__ and is_debug_session:
        ctx_buffer = WIRE_BUFFER_DEBUG
    else:
        ctx_buffer = WIRE_BUFFER

    thp_v3.set_buffer(ctx_buffer)

    # Take a mark of modules that are imported at this point, so we can
    # roll back and un-import any others.
    modules = utils.unimport_begin()

    while True:
        try:
            await thp_v3.thp_main_loop(iface, is_debug_session)

            if not __debug__ or not is_debug_session:
                # Unload modules imported by the workflow.  Should not raise.
                # This is not done for the debug session because the snapshot taken
                # in a debug session would clear modules which are in use by the
                # workflow running on wire.
                utils.unimport_end(modules)
                loop.clear()
                return

        except Exception as exc:
            # Log and try again. The session handler can only exit explicitly via
            # loop.clear() above.
            if __debug__:
                log.exception(__name__, exc)


async def handle_session(iface: WireInterface, is_debug_session: bool = False) -> None:
    if __debug__ and is_debug_session:
        ctx_buffer = WIRE_BUFFER_DEBUG
    else:
        ctx_buffer = WIRE_BUFFER
    ctx = context.CodecContext(iface, ctx_buffer)
    next_msg: protocol_common.Message | None = None

    if __debug__ and is_debug_session:
        import apps.debug

        apps.debug.DEBUG_CONTEXT = ctx

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
                        log.exception(__name__, exc)
                    await ctx.write(failure(exc))
                    continue

            else:
                # Process the message from previous run.
                msg = next_msg
                next_msg = None

            try:
                do_not_restart = await message_handler.handle_single_message(
                    ctx, msg, handler_finder=find_handler
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
                    log.exception(__name__, exc)
            finally:
                if not __debug__ or not is_debug_session:
                    # Unload modules imported by the workflow.  Should not raise.
                    # This is not done for the debug session because the snapshot taken
                    # in a debug session would clear modules which are in use by the
                    # workflow running on wire.
                    utils.unimport_end(modules)

                    if not do_not_restart:
                        # Let the session be restarted from `main`.
                        loop.clear()
                        return  # pylint: disable=lost-exception

        except Exception as exc:
            # Log and try again. The session handler can only exit explicitly via
            # loop.clear() above.
            if __debug__:
                log.exception(__name__, exc)
