"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec_v1.py` or `trezor/wire/thp_v1.py`.
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

from micropython import const  # pyright: ignore[reportMissingModuleSource]
from typing import TYPE_CHECKING  # pyright: ignore[reportShadowedImports]

from storage.cache_common import InvalidSessionError
from trezor import log, loop, protobuf, utils
from trezor.enums import FailureType
from trezor.messages import Failure
from trezor.wire import codec_v1, context, message_handler, protocol_common, thp_v1
from trezor.wire.errors import DataError, Error

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403


if TYPE_CHECKING:
    from trezorio import WireInterface  # pyright: ignore[reportMissingImports]
    from typing import (  # pyright: ignore[reportShadowedImports]
        Any,
        Callable,
        Container,
        Coroutine,
        TypeVar,
    )

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[[Msg], HandlerTask]
    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


# If set to False protobuf messages marked with "experimental_message" option are rejected.
EXPERIMENTAL_ENABLED = False


def setup(iface: WireInterface, is_debug_session: bool = False) -> None:
    """Initialize the wire stack on passed WireInterface."""
    if utils.USE_THP:
        loop.schedule(handle_thp_session(iface, is_debug_session))
    else:
        loop.schedule(handle_session(iface, codec_v1.SESSION_ID, is_debug_session))


def wrap_protobuf_load(
    buffer: bytes,
    expected_type: type[LoadedMessageType],
) -> LoadedMessageType:
    try:
        msg = protobuf.decode(buffer, expected_type, EXPERIMENTAL_ENABLED)
        if __debug__ and utils.EMULATOR:
            log.debug(
                __name__, "received message contents:\n%s", utils.dump_protobuf(msg)
            )
        return msg
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
        if e.args:
            raise DataError("Failed to decode message: " + " ".join(e.args))
        else:
            raise DataError("Failed to decode message")


_PROTOBUF_BUFFER_SIZE = const(8192)

WIRE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)

if __debug__:
    PROTOBUF_BUFFER_SIZE_DEBUG = 1024
    WIRE_BUFFER_DEBUG = bytearray(PROTOBUF_BUFFER_SIZE_DEBUG)


async def handle_thp_session(iface: WireInterface, is_debug_session: bool = False):
    if __debug__ and is_debug_session:
        ctx_buffer = WIRE_BUFFER_DEBUG
    else:
        ctx_buffer = WIRE_BUFFER

    thp_v1.set_buffer(ctx_buffer)

    if __debug__ and is_debug_session:
        import apps.debug

        print(apps.debug.DEBUG_CONTEXT)  # TODO remove

        # TODO add debug context or smth to apps.debug

    # Take a mark of modules that are imported at this point, so we can
    # roll back and un-import any others.
    modules = utils.unimport_begin()

    while True:
        try:
            await thp_v1.thp_main_loop(iface, is_debug_session)

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


async def handle_session(
    iface: WireInterface, codec_session_id: int, is_debug_session: bool = False
) -> None:
    if __debug__ and is_debug_session:
        ctx_buffer = WIRE_BUFFER_DEBUG
    else:
        ctx_buffer = WIRE_BUFFER
    session_id = codec_session_id.to_bytes(4, "big")
    ctx = context.CodecContext(iface, ctx_buffer, session_id)
    next_msg: protocol_common.MessageWithId | None = None

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

            # Set ctx.session_id to the value msg.session_id
            if msg.session_id is not None:
                ctx.channel_id = msg.session_id

            try:
                next_msg = await message_handler.handle_single_message(
                    ctx, msg, use_workflow=not is_debug_session
                )
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

                    if next_msg is None and msg.type not in AVOID_RESTARTING_FOR:
                        # Shut down the loop if there is no next message waiting.
                        # Let the session be restarted from `main`.
                        loop.clear()
                        return  # pylint: disable=lost-exception

        except Exception as exc:
            # Log and try again. The session handler can only exit explicitly via
            # loop.clear() above.
            if __debug__:
                log.exception(__name__, exc)


def _find_handler_placeholder(iface: WireInterface, msg_type: int) -> Handler | None:
    """Placeholder handler lookup before a proper one is registered."""
    return None


find_handler = _find_handler_placeholder
AVOID_RESTARTING_FOR: Container[int] = ()


def failure(exc: BaseException) -> Failure:
    if isinstance(exc, Error):
        return Failure(code=exc.code, message=exc.message)
    elif isinstance(exc, loop.TaskClosed):
        return Failure(code=FailureType.ActionCancelled, message="Cancelled")
    elif isinstance(exc, InvalidSessionError):
        return Failure(code=FailureType.InvalidSession, message="Invalid session")
    else:
        # NOTE: when receiving generic `FirmwareError` on non-debug build,
        # change the `if __debug__` to `if True` to get the full error message.
        if __debug__:
            message = str(exc)
        else:
            message = "Firmware error"
        return Failure(code=FailureType.FirmwareError, message=message)


def unexpected_message() -> Failure:
    return Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")
