from typing import TYPE_CHECKING

from trezor import log, loop, protobuf

from . import codec_v1

if TYPE_CHECKING:
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
    from trezorio import WireInterface

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[["Context", Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


class UnexpectedMessage(Exception):
    def __init__(self, msg: codec_v1.Message) -> None:
        super().__init__()
        self.msg = msg


class Context:
    def __init__(self, iface: WireInterface, sid: int, buffer: bytearray) -> None:
        self.iface = iface
        self.sid = sid
        self.buffer = buffer

    def read_from_wire(self) -> Awaitable[codec_v1.Message]:
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
    Wait until one of the passed tasks finishes, and return the result,
    while servicing the wire context.  If a message comes until one of the
    tasks ends, `UnexpectedMessageError` is raised.
    """
    if CURRENT_CONTEXT is None:
        return loop.race(*tasks)
    else:
        return loop.race(CURRENT_CONTEXT.read(()), *tasks)


async def call(
    msg: protobuf.MessageType,
    expected_type: type[LoadedMessageType],
) -> LoadedMessageType:
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")

    assert expected_type.MESSAGE_WIRE_TYPE is not None

    await CURRENT_CONTEXT.write(msg)
    del msg
    return await CURRENT_CONTEXT.read((expected_type.MESSAGE_WIRE_TYPE,), expected_type)


async def call_any(
    msg: protobuf.MessageType, *expected_wire_types: int
) -> protobuf.MessageType:
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")

    await CURRENT_CONTEXT.write(msg)
    del msg
    return await CURRENT_CONTEXT.read(expected_wire_types)


async def maybe_call(
    msg: protobuf.MessageType, expected_type: type[LoadedMessageType]
) -> None:
    if CURRENT_CONTEXT is None:
        return

    await call(msg, expected_type)


def get_context() -> Context:
    if CURRENT_CONTEXT is None:
        raise RuntimeError("No wire context")
    return CURRENT_CONTEXT


def with_context(ctx: Context, workflow: loop.Task) -> Generator:
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
