"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec_v1.py`.
- Transferred over USB interface, or UDP in case of Unix emulation.

This module:

1. Provides API for registering messages. In other words binds what functions are invoked
   when some particular message is received. See the `add` function.
2. Runs workflows, also called `handlers`, to process the message.
3. Creates and passes the `Context` object to the handlers. This provides an interface to
   wait, read, write etc. on the wire.

## `add` function

The `add` function registers what function is invoked when some particular `message_type`
is received. The following example binds the `apps.wallet.get_address` function with
the `GetAddress` message:

```python
wire.add(MessageType.GetAddress, "apps.wallet", "get_address")
```

## Session handler

When the `wire.setup` is called the `handle_session` coroutine is scheduled. The
`handle_session` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known the first handler is called. This way the
`handle_session` goes through all the workflows.

"""

from micropython import const
from typing import TYPE_CHECKING

from storage.cache import InvalidSessionError
from trezor import log, loop, protobuf, utils, workflow
from trezor.enums import FailureType
from trezor.messages import Failure
from trezor.wire import codec_v1
from trezor.wire.errors import ActionCancelled, DataError, Error

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403


if TYPE_CHECKING:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Container,
        Coroutine,
        Iterable,
        Protocol,
        TypeVar,
    )
    from trezorio import WireInterface

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[["Context", Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)

    class GenericContext(Protocol):
        async def call(
            self,
            msg: protobuf.MessageType,
            expected_type: type[protobuf.MessageType],
        ) -> Any:
            ...

        async def read(self, expected_type: type[protobuf.MessageType]) -> Any:
            ...

        async def write(self, msg: protobuf.MessageType) -> None:
            ...

        # XXX modify type signature so that the return value must be of the same type?
        async def wait(self, *tasks: Awaitable) -> Any:
            ...


# If set to False protobuf messages marked with "experimental_message" option are rejected.
experimental_enabled = False


def setup(iface: WireInterface, is_debug_session: bool = False) -> None:
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(handle_session(iface, codec_v1.SESSION_ID, is_debug_session))


def _wrap_protobuf_load(
    buffer: bytes,
    expected_type: type[LoadedMessageType],
) -> LoadedMessageType:
    try:
        msg = protobuf.decode(buffer, expected_type, experimental_enabled)
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


class DummyContext:
    async def call(self, *argv: Any) -> None:
        pass

    async def read(self, *argv: Any) -> None:
        pass

    async def write(self, *argv: Any) -> None:
        pass

    async def wait(self, *tasks: Awaitable) -> Any:
        return await loop.race(*tasks)


DUMMY_CONTEXT = DummyContext()

_PROTOBUF_BUFFER_SIZE = const(8192)

WIRE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)

if __debug__:
    PROTOBUF_BUFFER_SIZE_DEBUG = 1024
    WIRE_BUFFER_DEBUG = bytearray(PROTOBUF_BUFFER_SIZE_DEBUG)


class Context:
    def __init__(self, iface: WireInterface, sid: int, buffer: bytearray) -> None:
        self.iface = iface
        self.sid = sid
        self.buffer = buffer

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[LoadedMessageType],
    ) -> LoadedMessageType:
        await self.write(msg)
        del msg
        return await self.read(expected_type)

    async def call_any(
        self, msg: protobuf.MessageType, *expected_wire_types: int
    ) -> protobuf.MessageType:
        await self.write(msg)
        del msg
        return await self.read_any(expected_wire_types)

    def read_from_wire(self) -> Awaitable[codec_v1.Message]:
        return codec_v1.read_message(self.iface, self.buffer)

    async def read(self, expected_type: type[LoadedMessageType]) -> LoadedMessageType:
        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type.MESSAGE_NAME,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if msg.type != expected_type.MESSAGE_WIRE_TYPE:
            raise UnexpectedMessageError(msg)

        if __debug__:
            log.debug(
                __name__,
                "%s:%x read: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type.MESSAGE_NAME,
            )

        # look up the protobuf class and parse the message
        return _wrap_protobuf_load(msg.data, expected_type)

    async def read_any(
        self, expected_wire_types: Iterable[int]
    ) -> protobuf.MessageType:
        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_wire_types,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if msg.type not in expected_wire_types:
            raise UnexpectedMessageError(msg)

        # find the protobuf type
        exptype = protobuf.type_for_wire(msg.type)

        if __debug__:
            log.debug(
                __name__,
                "%s:%x read: %s",
                self.iface.iface_num(),
                self.sid,
                exptype.MESSAGE_NAME,
            )

        # parse the message and return it
        return _wrap_protobuf_load(msg.data, exptype)

    async def write(self, msg: protobuf.MessageType) -> None:
        if __debug__:
            log.debug(
                __name__,
                "%s:%x write: %s",
                self.iface.iface_num(),
                self.sid,
                msg.MESSAGE_NAME,
            )

        # cannot write message without wire type
        assert msg.MESSAGE_WIRE_TYPE is not None

        msg_size = protobuf.encoded_length(msg)

        if msg_size <= len(self.buffer):
            # reuse preallocated
            buffer = self.buffer
        else:
            # message is too big, we need to allocate a new buffer
            buffer = bytearray(msg_size)

        msg_size = protobuf.encode(buffer, msg)

        await codec_v1.write_message(
            self.iface,
            msg.MESSAGE_WIRE_TYPE,
            memoryview(buffer)[:msg_size],
        )

    def wait(self, *tasks: Awaitable) -> Any:
        """
        Wait until one of the passed tasks finishes, and return the result,
        while servicing the wire context.  If a message comes until one of the
        tasks ends, `UnexpectedMessageError` is raised.
        """
        return loop.race(self.read_any(()), *tasks)


class UnexpectedMessageError(Exception):
    def __init__(self, msg: codec_v1.Message) -> None:
        super().__init__()
        self.msg = msg


async def _handle_single_message(
    ctx: Context, msg: codec_v1.Message, use_workflow: bool
) -> codec_v1.Message | None:
    """Handle a message that was loaded from USB by the caller.

    Find the appropriate handler, run it and write its result on the wire. In case
    a problem is encountered at any point, write the appropriate error on the wire.

    If the workflow finished normally or with an error, the return value is None.

    If an unexpected message had arrived on the wire while the workflow was processing,
    the workflow is shut down with an `UnexpectedMessageError`. This is not considered
    an "error condition" to return over the wire -- instead the message is processed
    as if starting a new workflow.
    In such case, the `UnexpectedMessageError` is caught and the message is returned
    to the caller. It will then be processed in the next iteration of the message loop.
    """
    if __debug__:
        try:
            msg_type = protobuf.type_for_wire(msg.type).MESSAGE_NAME
        except Exception:
            msg_type = f"{msg.type} - unknown message type"
        log.debug(
            __name__,
            "%s:%x receive: <%s>",
            ctx.iface.iface_num(),
            ctx.sid,
            msg_type,
        )

    res_msg: protobuf.MessageType | None = None

    # We need to find a handler for this message type.  Should not raise.
    handler = find_handler(ctx.iface, msg.type)  # pylint: disable=assignment-from-none

    if handler is None:
        # If no handler is found, we can skip decoding and directly
        # respond with failure.
        await ctx.write(unexpected_message())
        return None

    if msg.type in workflow.ALLOW_WHILE_LOCKED:
        workflow.autolock_interrupts_workflow = False

    # Here we make sure we always respond with a Failure response
    # in case of any errors.
    try:
        # Find a protobuf.MessageType subclass that describes this
        # message.  Raises if the type is not found.
        req_type = protobuf.type_for_wire(msg.type)

        # Try to decode the message according to schema from
        # `req_type`. Raises if the message is malformed.
        req_msg = _wrap_protobuf_load(msg.data, req_type)

        # Create the handler task.
        task = handler(ctx, req_msg)

        # Run the workflow task.  Workflow can do more on-the-wire
        # communication inside, but it should eventually return a
        # response message, or raise an exception (a rather common
        # thing to do).  Exceptions are handled in the code below.
        if use_workflow:
            # Spawn a workflow around the task. This ensures that concurrent
            # workflows are shut down.
            res_msg = await workflow.spawn(task)
        else:
            # For debug messages, ignore workflow processing and just await
            # results of the handler.
            res_msg = await task

    except UnexpectedMessageError as exc:
        # Workflow was trying to read a message from the wire, and
        # something unexpected came in.  See Context.read() for
        # example, which expects some particular message and raises
        # UnexpectedMessageError if another one comes in.
        # In order not to lose the message, we return it to the caller.
        # TODO:
        # We might handle only the few common cases here, like
        # Initialize and Cancel.
        return exc.msg

    except BaseException as exc:
        # Either:
        # - the message had a type that has a registered handler, but does not have
        #   a protobuf class
        # - the message was not valid protobuf
        # - workflow raised some kind of an exception while running
        # - something canceled the workflow from the outside
        if __debug__:
            if isinstance(exc, ActionCancelled):
                log.debug(__name__, "cancelled: %s", exc.message)
            elif isinstance(exc, loop.TaskClosed):
                log.debug(__name__, "cancelled: loop task was closed")
            else:
                log.exception(__name__, exc)
        res_msg = failure(exc)

    if res_msg is not None:
        # perform the write outside the big try-except block, so that usb write
        # problem bubbles up
        await ctx.write(res_msg)
    return None


async def handle_session(
    iface: WireInterface, session_id: int, is_debug_session: bool = False
) -> None:
    if __debug__ and is_debug_session:
        ctx_buffer = WIRE_BUFFER_DEBUG
    else:
        ctx_buffer = WIRE_BUFFER

    ctx = Context(iface, session_id, ctx_buffer)
    next_msg: codec_v1.Message | None = None

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
                except codec_v1.CodecError as exc:
                    if __debug__:
                        log.exception(__name__, exc)
                    await ctx.write(failure(exc))
                    continue

            else:
                # Process the message from previous run.
                msg = next_msg
                next_msg = None

            try:
                next_msg = await _handle_single_message(
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
