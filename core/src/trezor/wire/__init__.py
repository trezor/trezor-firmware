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

from trezorutils import (
    protobuf_decode,
    protobuf_encode,
    protobuf_len,
    protobuf_type_for_wire,
)

import protobuf
from trezor import log, loop, messages, ui, utils, workflow
from trezor.messages import Failure, FailureType
from trezor.wire import codec_v1
from trezor.wire.errors import ActionCancelled, DataError, Error

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403

if False:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Coroutine,
        Iterable,
        TypeVar,
    )
    from trezorio import WireInterface

    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[["Context", Msg], HandlerTask]


# Maps a wire type directly to a handler.
workflow_handlers: dict[int, Handler] = {}

# Maps a wire type to a tuple of package and module.  This allows handlers
# to be dynamically imported when such message arrives.
workflow_packages: dict[int, tuple[str, str]] = {}

# If set to False protobuf messages marked with "unstable" option are rejected.
experimental_enabled: bool = False


def add(wire_type: int, pkgname: str, modname: str) -> None:
    """Shortcut for registering a dynamically-imported Protobuf workflow."""
    workflow_packages[wire_type] = (pkgname, modname)


def register(wire_type: int, handler: Handler) -> None:
    """Register `handler` to get scheduled after `wire_type` message is received."""
    workflow_handlers[wire_type] = handler


def setup(iface: WireInterface, use_workflow: bool = True) -> None:
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(handle_session(iface, codec_v1.SESSION_ID, use_workflow))


def clear() -> None:
    """Remove all registered handlers."""
    workflow_handlers.clear()
    workflow_packages.clear()


if False:
    from typing import Protocol

    class GenericContext(Protocol):
        async def call(
            self,
            msg: protobuf.MessageType,
            expected_type: type[protobuf.LoadedMessageType],
        ) -> Any:
            ...

        async def read(self, expected_type: type[protobuf.LoadedMessageType]) -> Any:
            ...

        async def write(self, msg: protobuf.MessageType) -> None:
            ...

        # XXX modify type signature so that the return value must be of the same type?
        async def wait(self, *tasks: Awaitable) -> Any:
            ...


def _wrap_protobuf_load(
    reader: protobuf.Reader,
    expected_type: type[protobuf.LoadedMessageType],
) -> protobuf.LoadedMessageType:
    try:
        return protobuf_decode(reader.buffer, expected_type, experimental_enabled)
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
        if e.args:
            raise DataError("Failed to decode message: {}".format(e.args[0]))
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

PROTOBUF_BUFFER_SIZE = 8192


class Context:
    def __init__(self, iface: WireInterface, sid: int) -> None:
        self.iface = iface
        self.sid = sid
        self.buffer = bytearray(PROTOBUF_BUFFER_SIZE)

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[protobuf.LoadedMessageType],
    ) -> protobuf.LoadedMessageType:
        await self.write(msg)
        del msg
        return await self.read(expected_type)

    async def call_any(
        self, msg: protobuf.MessageType, *expected_wire_types: int
    ) -> protobuf.MessageType:
        await self.write(msg)
        del msg
        return await self.read_any(expected_wire_types)

    def read_from_wire(self) -> codec_v1.Message:
        return codec_v1.read_message(self.iface, self.buffer)

    async def read(
        self,
        expected_type: type[protobuf.LoadedMessageType],
    ) -> protobuf.LoadedMessageType:
        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if msg.type != expected_type.wire():
            raise UnexpectedMessageError(msg)

        if __debug__:
            log.debug(
                __name__,
                "%s:%x read: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type,
            )

        workflow.idle_timer.touch()

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
        exptype = protobuf_type_for_wire(msg.type)

        if __debug__:
            log.debug(
                __name__, "%s:%x read: %s", self.iface.iface_num(), self.sid, exptype
            )

        workflow.idle_timer.touch()

        # parse the message and return it
        return _wrap_protobuf_load(msg.data, exptype)

    async def write(self, msg: protobuf.MessageType) -> None:
        if __debug__:
            log.debug(
                __name__, "%s:%x write: %s", self.iface.iface_num(), self.sid, msg
            )

        msg_type = msg.MESSAGE_WIRE_TYPE
        pbuf_type = protobuf_type_for_wire(msg_type)
        msg_size = protobuf_len(pbuf_type, msg)

        if msg_size <= len(self.buffer):
            # reuse preallocated
            buffer = self.buffer
        else:
            # message is too big, we need to allocate a new buffer
            buffer = bytearray(msg_size)

        msg_size = protobuf_encode(buffer, pbuf_type, msg)

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


async def handle_session(
    iface: WireInterface, session_id: int, use_workflow: bool = True
) -> None:
    ctx = Context(iface, session_id)
    next_msg: codec_v1.Message | None = None
    res_msg: protobuf.MessageType | None = None
    req_type = None
    req_msg = None
    while True:
        try:
            if next_msg is None:
                # We are not currently reading a message, so let's wait for one.
                # If the decoding fails, exception is raised and we try again
                # (with the same `Reader` instance, it's OK).  Even in case of
                # de-synchronized wire communication, report with a message
                # header is eventually received, after a couple of tries.
                msg = await ctx.read_from_wire()

                if __debug__:
                    try:
                        msg_type = "MsgDef"
                        # msg_type = protobuf_type_for_wire(msg.type).__name__
                    except KeyError:
                        msg_type = "%d - unknown message type" % msg.type
                    log.debug(
                        __name__,
                        "%s:%x receive: <%s>",
                        iface.iface_num(),
                        session_id,
                        msg_type,
                    )
            else:
                # We have a reader left over from earlier.  We should process
                # this message instead of waiting for new one.
                msg = next_msg
                next_msg = None

            # Now we are in a middle of reading a message and we need to decide
            # what to do with it, based on its type from the message header.
            # From this point on, we should take care to read it in full and
            # send a response.

            # Take a mark of modules that are imported at this point, so we can
            # roll back and un-import any others.  Should not raise.
            modules = utils.unimport_begin()

            # We need to find a handler for this message type.  Should not
            # raise.
            handler = find_handler(iface, msg.type)

            if handler is None:
                # If no handler is found, we can skip decoding and directly
                # respond with failure.  Should not raise.
                res_msg = unexpected_message()

            else:
                # We found a valid handler for this message type.

                # Workflow task, declared for the finally block
                wf_task: HandlerTask | None = None

                # Here we make sure we always respond with a Failure response
                # in case of any errors.
                try:
                    # Find a protobuf.MessageType subclass that describes this
                    # message.  Raises if the type is not found.
                    req_type = protobuf_type_for_wire(msg.type)

                    # Try to decode the message according to schema from
                    # `req_type`. Raises if the message is malformed.
                    req_msg = _wrap_protobuf_load(msg.data, req_type)

                    # At this point, message reports are all processed and
                    # correctly parsed into `req_msg`.

                    # Create the workflow task.
                    wf_task = handler(ctx, req_msg)

                    # Run the workflow task.  Workflow can do more on-the-wire
                    # communication inside, but it should eventually return a
                    # response message, or raise an exception (a rather common
                    # thing to do).  Exceptions are handled in the code below.
                    if use_workflow:
                        res_msg = await workflow.spawn(wf_task)
                    else:
                        res_msg = await wf_task

                except UnexpectedMessageError as exc:
                    # Workflow was trying to read a message from the wire, and
                    # something unexpected came in.  See Context.read() for
                    # example, which expects some particular message and raises
                    # UnexpectedMessageError if another one comes in.
                    # In order not to lose the message, we pass on the reader
                    # to get picked up by the workflow logic in the beginning of
                    # the cycle, which processes it in the usual manner.
                    # TODO:
                    # We might handle only the few common cases here, like
                    # Initialize and Cancel.
                    next_msg = exc.msg
                    res_msg = None

                except Exception as exc:
                    # Either:
                    # - the first workflow message had a type that has a
                    #   registered handler, but does not have a protobuf class
                    # - the first workflow message was not a valid protobuf
                    # - workflow raised some kind of an exception while running
                    # - something canceled the workflow from the outside
                    if __debug__:
                        if isinstance(exc, ActionCancelled):
                            log.debug(__name__, "cancelled: {}".format(exc.message))
                        elif isinstance(exc, loop.TaskClosed):
                            log.debug(__name__, "cancelled: loop task was closed")
                        else:
                            log.exception(__name__, exc)
                    res_msg = failure(exc)

                finally:
                    # If we ran a workflow task, and a default workflow is on, make sure
                    # we do not race against the layout that is inside.
                    # TODO: this is very hacky and complects wire with the ui
                    if wf_task is not None and workflow.default_task is not None:
                        await ui.wait_until_layout_is_running()

            if res_msg is not None:
                # Either the workflow returned a response, or we created one.
                # Write it on the wire.  Possibly, the incoming message haven't
                # been read in full.  We ignore this case here and let the rest
                # of the reports get processed while waiting for the message
                # header.
                # TODO: if the write fails, we do not unimport the loaded modules
                await ctx.write(res_msg)

            # Cleanup, so garbage collection triggered after un-importing can
            # pick up the trash.
            req_type = None
            req_msg = None
            res_msg = None
            handler = None
            wf_task = None

            # Unload modules imported by the workflow.  Should not raise.
            utils.unimport_end(modules)

        except Exception as exc:
            # The session handling should never exit, just log and continue.
            if __debug__:
                log.exception(__name__, exc)


def find_registered_workflow_handler(
    iface: WireInterface, msg_type: int
) -> Handler | None:
    if msg_type in workflow_handlers:
        # Message has a handler available, return it directly.
        handler = workflow_handlers[msg_type]

    elif msg_type in workflow_packages:
        # Message needs a dynamically imported handler, import it.
        pkgname, modname = workflow_packages[msg_type]
        handler = import_workflow(pkgname, modname)

    else:
        # Message does not have any registered handler.
        return None

    return handler


find_handler = find_registered_workflow_handler


def import_workflow(pkgname: str, modname: str) -> Any:
    modpath = "%s.%s" % (pkgname, modname)
    module = __import__(modpath, None, None, (modname,), 0)
    handler = getattr(module, modname)
    return handler


def failure(exc: BaseException) -> Failure:
    if isinstance(exc, Error):
        return Failure(code=exc.code, message=exc.message)
    elif isinstance(exc, loop.TaskClosed):
        return Failure(code=FailureType.ActionCancelled, message="Cancelled")
    else:
        return Failure(code=FailureType.FirmwareError, message="Firmware error")


def unexpected_message() -> Failure:
    return Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")
