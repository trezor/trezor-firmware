"""Context pseudo-global.

Each workflow handler runs in a "context" which is tied to a particular communication
session. When the handler needs to communicate with the host, it needs access to that
context.

To avoid the need to pass a context object around, the context is stored in a
pseudo-global manner: any workflow handler can request access to the context via this
module, and the appropriate context object will be used for it.

Some workflows don't need a context to exist. This is supported by the `maybe_call`
function, which will silently ignore the call if no context is available. Useful mainly
for ButtonRequests. Of course, `context.wait()` transparently works in such situations.
"""

from typing import TYPE_CHECKING

from trezor import log, loop, protobuf

from . import codec_v1

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import (
        Any,
        Awaitable,
        Callable,
        Container,
        Coroutine,
        Generator,
        TypeVar,
        overload,
    )

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[["Context", Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


class UnexpectedMessage(Exception):
    """A message was received that is not part of the current workflow.

    Utility exception to inform the session handler that the current workflow
    should be aborted and a new one started as if `msg` was the first message.
    """

    def __init__(self, msg: codec_v1.Message) -> None:
        super().__init__()
        self.msg = msg


class Context:
    """Wire context.

    Represents USB communication inside a particular session on a particular interface
    (i.e., wire, debug, single BT connection, etc.)
    """

    def __init__(self, iface: WireInterface, sid: int, buffer: bytearray) -> None:
        self.iface = iface
        self.sid = sid
        self.buffer = buffer

    def read_from_wire(self) -> Awaitable[codec_v1.Message]:
        """Read a whole message from the wire without parsing it."""
        return codec_v1.read_message(self.iface, self.buffer)

    if TYPE_CHECKING:

        @overload
        async def read(self, expected_types: Container[int]) -> protobuf.MessageType:
            ...

        @overload
        async def read(
            self, expected_types: Container[int], expected_type: type[LoadedMessageType]
        ) -> LoadedMessageType:
            ...

    async def read(
        self,
        expected_types: Container[int],
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        """Read a message from the wire.

        The read message must be of one of the types specified in `expected_types`.
        If only a single type is expected, it can be passed as `expected_type`,
        to save on having to decode the type code into a protobuf class.
        """
        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type.MESSAGE_NAME if expected_type else expected_types,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if msg.type not in expected_types:
            raise UnexpectedMessage(msg)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(msg.type)

        if __debug__:
            log.debug(
                __name__,
                "%s:%x read: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type.MESSAGE_NAME,
            )

        # look up the protobuf class and parse the message
        from . import wrap_protobuf_load

        return wrap_protobuf_load(msg.data, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        """Write a message to the wire."""
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


CURRENT_CONTEXT: Context | None = None


def wait(*tasks: Awaitable) -> Any:
    """
    Wait until one of the passed tasks finishes, and return the result, while servicing
    the wire context.

    Used to make sure the device is responsive on USB while waiting for user
    interaction. If a message is received before any of the passed in tasks finish, it
    raises an `UnexpectedMessage` exception, returning control to the session handler.
    """
    if CURRENT_CONTEXT is None:
        return loop.race(*tasks)
    else:
        return loop.race(CURRENT_CONTEXT.read(()), *tasks)


async def call(
    msg: protobuf.MessageType,
    expected_type: type[LoadedMessageType],
) -> LoadedMessageType:
    """Send a message to the host and wait for a response of a particular type.

    Raises if there is no context for this workflow."""
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")

    assert expected_type.MESSAGE_WIRE_TYPE is not None

    await CURRENT_CONTEXT.write(msg)
    del msg
    return await CURRENT_CONTEXT.read((expected_type.MESSAGE_WIRE_TYPE,), expected_type)


async def call_any(
    msg: protobuf.MessageType, *expected_wire_types: int
) -> protobuf.MessageType:
    """Send a message to the host and wait for a response.

    The response can be of any of the types specified in `expected_wire_types`.

    Raises if there is no context for this workflow."""
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")

    await CURRENT_CONTEXT.write(msg)
    del msg
    return await CURRENT_CONTEXT.read(expected_wire_types)


async def maybe_call(
    msg: protobuf.MessageType, expected_type: type[LoadedMessageType]
) -> None:
    """Send a message to the host and read but ignore the response.

    If there is a context, the function still checks that the response is of the
    requested type. If there is no context, the call is ignored.
    """
    if CURRENT_CONTEXT is None:
        return

    await call(msg, expected_type)


def get_context() -> Context:
    """Get the current session context.

    Can be needed in case the caller needs raw read and raw write capabilities, which
    are not provided by the module functions.

    Result of this function should not be stored -- the context is technically allowed
    to change inbetween any `await` statements.
    """
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")
    return CURRENT_CONTEXT


def with_context(ctx: Context, workflow: loop.Task) -> Generator:
    """Run a workflow in a particular context.

    Stores the context in a closure and installs it into the global variable every time
    the closure is resumed, thus making sure that all calls to `wire.context.*` will
    work as expected.
    """
    global CURRENT_CONTEXT
    send_val = None
    send_exc = None

    while True:
        CURRENT_CONTEXT = ctx
        try:
            if send_exc is not None:
                res = workflow.throw(send_exc)
            else:
                res = workflow.send(send_val)
        except StopIteration as st:
            return st.value
        finally:
            CURRENT_CONTEXT = None

        try:
            send_val = yield res
        except BaseException as e:
            send_exc = e
        else:
            send_exc = None
