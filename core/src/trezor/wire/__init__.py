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

import protobuf
from trezor import log, loop, messages, utils, workflow
from trezor.messages import FailureType
from trezor.messages.Failure import Failure
from trezor.wire import codec_v1
from trezor.wire.errors import Error

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403

if False:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Dict,
        Iterable,
        List,
        Optional,
        Tuple,
        Type,
    )
    from trezorio import WireInterface

    Handler = Callable[..., loop.Task]


# Maps a wire type directly to a handler.
workflow_handlers = {}  # type: Dict[int, Handler]

# Maps a wire type to a tuple of package and module.  This allows handlers
# to be dynamically imported when such message arrives.
workflow_packages = {}  # type: Dict[int, Tuple[str, str]]

# Maps a wire type to a "keychain namespace".  Such workflows are created
# with an instance of `seed.Keychain` with correctly derived keys.
workflow_namespaces = {}  # type: Dict[int, List]


def add(wire_type: int, pkgname: str, modname: str, namespace: List = None) -> None:
    """Shortcut for registering a dynamically-imported Protobuf workflow."""
    if namespace is not None:
        workflow_namespaces[wire_type] = namespace
    workflow_packages[wire_type] = (pkgname, modname)


def register(wire_type: int, handler: Handler) -> None:
    """Register `handler` to get scheduled after `wire_type` message is received."""
    workflow_handlers[wire_type] = handler


def setup(iface: WireInterface) -> None:
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(handle_session(iface, codec_v1.SESSION_ID))


def clear() -> None:
    """Remove all registered handlers."""
    workflow_handlers.clear()
    workflow_packages.clear()
    workflow_namespaces.clear()


class DummyContext:
    async def call(*argv: Any) -> None:
        pass

    async def read(*argv: Any) -> None:
        pass

    async def write(*argv: Any) -> None:
        pass

    async def wait(self, *tasks: Awaitable) -> Any:
        return await loop.race(*tasks)


class Context:
    def __init__(self, iface: WireInterface, sid: int) -> None:
        self.iface = iface
        self.sid = sid

    async def call(
        self, msg: protobuf.MessageType, expected_type: Type[protobuf.LoadedMessageType]
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

    async def read(
        self, expected_type: Type[protobuf.LoadedMessageType]
    ) -> protobuf.LoadedMessageType:
        reader = self.make_reader()

        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type,
            )

        # Wait for the message header, contained in the first report.  After
        # we receive it, we have a message type to match on.
        await reader.aopen()

        # If we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if reader.type != expected_type.MESSAGE_WIRE_TYPE:
            raise UnexpectedMessageError(reader)

        if __debug__:
            log.debug(
                __name__,
                "%s:%x read: %s",
                self.iface.iface_num(),
                self.sid,
                expected_type,
            )

        # parse the message and return it
        return await protobuf.load_message(reader, expected_type)

    async def read_any(
        self, expected_wire_types: Iterable[int]
    ) -> protobuf.MessageType:
        reader = self.make_reader()

        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                expected_wire_types,
            )

        # Wait for the message header, contained in the first report.  After
        # we receive it, we have a message type to match on.
        await reader.aopen()

        # If we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if reader.type not in expected_wire_types:
            raise UnexpectedMessageError(reader)

        # find the protobuf type
        exptype = messages.get_type(reader.type)

        if __debug__:
            log.debug(
                __name__, "%s:%x read: %s", self.iface.iface_num(), self.sid, exptype
            )

        # parse the message and return it
        return await protobuf.load_message(reader, exptype)

    async def write(self, msg: protobuf.MessageType) -> None:
        writer = self.make_writer()

        if __debug__:
            log.debug(
                __name__, "%s:%x write: %s", self.iface.iface_num(), self.sid, msg
            )

        # get the message size
        fields = msg.get_fields()
        size = protobuf.count_message(msg, fields)

        # write the message
        writer.setheader(msg.MESSAGE_WIRE_TYPE, size)
        await protobuf.dump_message(writer, msg, fields)
        await writer.aclose()

    def wait(self, *tasks: Awaitable) -> Any:
        """
        Wait until one of the passed tasks finishes, and return the result,
        while servicing the wire context.  If a message comes until one of the
        tasks ends, `UnexpectedMessageError` is raised.
        """
        return loop.race(self.read_any(()), *tasks)

    def make_reader(self) -> codec_v1.Reader:
        return codec_v1.Reader(self.iface)

    def make_writer(self) -> codec_v1.Writer:
        return codec_v1.Writer(self.iface)


class UnexpectedMessageError(Exception):
    def __init__(self, reader: codec_v1.Reader) -> None:
        self.reader = reader


async def handle_session(iface: WireInterface, session_id: int) -> None:
    ctx = Context(iface, session_id)
    next_reader = None  # type: Optional[codec_v1.Reader]
    while True:
        try:
            if next_reader is None:
                # We are not currently reading a message, so let's wait for one.
                # If the decoding fails, exception is raised and we try again
                # (with the same `Reader` instance, it's OK).  Even in case of
                # de-synchronized wire communication, report with a message
                # header is eventually received, after a couple of tries.
                req_reader = ctx.make_reader()
                await req_reader.aopen()

                if __debug__:
                    log.debug(
                        __name__,
                        "%s:%x receive: %s",
                        iface.iface_num(),
                        session_id,
                        req_reader.type,
                    )
            else:
                # We have a reader left over from earlier.  We should process
                # this message instead of waiting for new one.
                req_reader = next_reader
                next_reader = None

            # Now we are in a middle of reading a message and we need to decide
            # what to do with it, based on its type from the message header.
            # From this point on, we should take care to read it in full and
            # send a response.

            # Take a mark of modules that are imported at this point, so we can
            # roll back and un-import any others.  Should not raise.
            modules = utils.unimport_begin()

            # We need to find a handler for this message type.  Should not
            # raise.
            handler = get_workflow_handler(req_reader)

            if handler is None:
                # If no handler is found, we can skip decoding and directly
                # respond with failure, but first, we should read the rest of
                # the message reports.  Should not raise.
                await read_and_throw_away(req_reader)
                res_msg = unexpected_message()

            else:
                # We found a valid handler for this message type.

                # Workflow task, declared for the `workflow.on_close` call later.
                wf_task = None  # type: Optional[loop.Task]

                # Here we make sure we always respond with a Failure response
                # in case of any errors.
                try:
                    # Find a protobuf.MessageType subclass that describes this
                    # message.  Raises if the type is not found.
                    req_type = messages.get_type(req_reader.type)

                    # Try to decode the message according to schema from
                    # `req_type`. Raises if the message is malformed.
                    req_msg = await protobuf.load_message(req_reader, req_type)

                    # At this point, message reports are all processed and
                    # correctly parsed into `req_msg`.

                    # Create the workflow task.
                    wf_task = handler(ctx, req_msg)

                    # Register the task into the workflow management system.
                    workflow.on_start(wf_task)

                    # Run the workflow task.  Workflow can do more on-the-wire
                    # communication inside, but it should eventually return a
                    # response message, or raise an exception (a rather common
                    # thing to do).  Exceptions are handled in the code below.
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
                    next_reader = exc.reader
                    res_msg = None

                except Exception as exc:
                    # Either:
                    # - the first workflow message had a type that has a
                    #   registered handler, but does not have a protobuf class
                    # - the first workflow message was not a valid protobuf
                    # - workflow raised some kind of an exception while running
                    if __debug__:
                        log.exception(__name__, exc)
                    res_msg = failure(exc)

                finally:
                    # De-register the task from the workflow system, if we
                    # registered it before.
                    if wf_task is not None:
                        workflow.on_close(wf_task)

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
            req_reader = None
            req_type = None
            req_msg = None
            res_msg = None
            handler = None
            wf_task = None

            # Unload modules imported by the workflow.  Should not raise.
            utils.unimport_end(modules)

        except BaseException as exc:
            # The session handling should never exit, just log and continue.
            if __debug__:
                log.exception(__name__, exc)


def get_workflow_handler(reader: codec_v1.Reader) -> Optional[Handler]:
    msg_type = reader.type

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

    if msg_type in workflow_namespaces:
        # Workflow needs a keychain, wrap it with a keychain provider.
        namespace = workflow_namespaces[msg_type]
        handler = wrap_keychain_workflow(handler, namespace)

    return handler


def import_workflow(pkgname: str, modname: str) -> Handler:
    modpath = "%s.%s" % (pkgname, modname)
    module = __import__(modpath, None, None, (modname,), 0)  # type: ignore
    handler = getattr(module, modname)
    return handler


def wrap_keychain_workflow(handler: Handler, namespace: List) -> Handler:
    async def keychain_workflow(ctx: Context, req: protobuf.MessageType) -> Any:
        from apps.common import seed

        # Workflow that is hiding behind `handler` expects a keychain
        # instance, in addition to the request message.  Acquire it from
        # the seed module.  More on-the-wire communication, and also UI
        # interaction, might happen here.
        keychain = await seed.get_keychain(ctx, namespace)
        try:
            return await handler(ctx, req, keychain)
        finally:
            # Be hygienic and wipe the keys from memory.
            keychain.__del__()

    return keychain_workflow


def failure(exc: BaseException) -> Failure:
    if isinstance(exc, Error):
        return Failure(code=exc.code, message=exc.message)
    else:
        return Failure(code=FailureType.FirmwareError, message="Firmware error")


def unexpected_message() -> Failure:
    return Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")


async def read_and_throw_away(reader: codec_v1.Reader) -> None:
    while reader.size > 0:
        buf = bytearray(reader.size)
        await reader.areadinto(buf)
