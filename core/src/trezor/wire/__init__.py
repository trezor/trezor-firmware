"""
# Wire

Implements wire, which:

1. Provides API for registering messages. In other words binds what functions are invoked
when some particular message is received. See the `add` function.
2. Runs workflows, also called `handlers` to process the message.
3. Creates and passes on the `Context` object to the endpoint functions. This provides
the functions an interface to wait, read, write etc. on the wire.

## `add` function

The `add` function registers what function is invoked when some particular `message_type`
is received. The following example binds the `apps.wallet.get_address` function with
the GetAddress message:

```python
wire.add(MessageType.GetAddress, "apps.wallet", "get_address")
```

## `register` function

The `add` is shortcut for the `register` function, which registers what workflows are to
be run in an onion-like structure. The number of workflows is variable and workflows can
have variable amount of arguments. This is best explained on an example:

```python
register(
        MessageType.GetAddress,
        protobuf_workflow,
        keychain_workflow,
        namespace,
        import_workflow,
        "apps.wallet",
        "get_address",
)
```

In the example above we can see that for the message GetAddress a number of workflows
is invoked.
1. `protobuf_workflow` with no arguments.
2. `keychain_workflow` with a single argument `namespace`.
3. `import_workflow` with two str arguments.

The `register` function adds the workflows to the `workflow_handlers` global variable in
the format of Dict[message_type, Tuple[handler, args]]. Taken the example above the
`register` function adds this to the Dict:

```
workflow_handlers[MessageType.GetAddress] = (protobuf_workflow, args)
```

where `args` is the rest of arguments as described above.

## Session handler

When the `wire.setup` is called the `session_handler` coroutine is scheduled. The
`session_handler` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known (in other words the
`workflow_handlers` Dict has this specific key) the first handler is called. This way the
`session_handler` goes through all the workflows.

"""

import protobuf
from trezor import log, loop, messages, utils, workflow
from trezor.messages import FailureType
from trezor.wire import codec_v1
from trezor.wire.errors import Error

# import all errors into namespace, so that `wire.Error` is available elsewhere
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403

if False:
    from typing import (
        Any,
        Awaitable,
        Dict,
        Callable,
        Iterable,
        List,
        Optional,
        Tuple,
        Type,
    )
    from trezorio import WireInterface
    from protobuf import LoadedMessageType, MessageType

    Handler = Callable[..., loop.Task]


workflow_handlers = {}  # type: Dict[int, Tuple[Handler, Iterable]]


def add(mtype: int, pkgname: str, modname: str, namespace: List = None) -> None:
    """Shortcut for registering a dynamically-imported Protobuf workflow."""
    if namespace is not None:
        register(
            mtype,
            protobuf_workflow,
            keychain_workflow,
            namespace,
            import_workflow,
            pkgname,
            modname,
        )
    else:
        register(mtype, protobuf_workflow, import_workflow, pkgname, modname)


def register(message_type: int, handler: Handler, *args: Any) -> None:
    """Register `handler` to get scheduled after `message_type` message is received."""
    if isinstance(message_type, type) and issubclass(
        message_type, protobuf.MessageType
    ):
        # Q: shouldn't we use one or another? This is weird to support both
        message_type = message_type.MESSAGE_WIRE_TYPE
    if message_type in workflow_handlers:
        raise KeyError
    workflow_handlers[message_type] = (handler, args)


def setup(iface: WireInterface) -> None:
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(session_handler(iface, codec_v1.SESSION_ID))


def clear() -> None:
    """Remove all registered handlers."""
    workflow_handlers.clear()


class DummyContext:
    async def call(*argv):
        pass

    async def read(*argv):
        pass

    async def write(*argv):
        pass

    async def wait(self, *tasks: Awaitable) -> Any:
        return await loop.race(*tasks)


class Context:
    def __init__(self, iface: WireInterface, sid: int) -> None:
        self.iface = iface
        self.sid = sid

    async def call(
        self, msg: MessageType, exptype: Type[LoadedMessageType]
    ) -> LoadedMessageType:
        await self.write(msg)
        del msg
        return await self.read(exptype)

    async def call_any(self, msg: MessageType, *allowed_types: int) -> MessageType:
        await self.write(msg)
        del msg
        return await self.read_any(allowed_types)

    async def read(
        self, exptype: Optional[Type[LoadedMessageType]]
    ) -> LoadedMessageType:
        reader = self.make_reader()

        if __debug__:
            log.debug(
                __name__, "%s:%x expect: %s", self.iface.iface_num(), self.sid, exptype
            )

        await reader.aopen()  # wait for the message header

        # if we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it
        if exptype is None or reader.type != exptype.MESSAGE_WIRE_TYPE:
            raise UnexpectedMessageError(reader)

        if __debug__:
            log.debug(
                __name__, "%s:%x read: %s", self.iface.iface_num(), self.sid, exptype
            )

        # parse the message and return it
        return await protobuf.load_message(reader, exptype)

    async def read_any(self, allowed_types: Iterable[int]) -> MessageType:
        reader = self.make_reader()

        if __debug__:
            log.debug(
                __name__,
                "%s:%x expect: %s",
                self.iface.iface_num(),
                self.sid,
                allowed_types,
            )

        await reader.aopen()  # wait for the message header

        # if we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it
        if reader.type not in allowed_types:
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
        return loop.race(self.read(None), *tasks)

    def make_reader(self) -> codec_v1.Reader:
        return codec_v1.Reader(self.iface)

    def make_writer(self) -> codec_v1.Writer:
        return codec_v1.Writer(self.iface)


class UnexpectedMessageError(Exception):
    def __init__(self, reader: codec_v1.Reader) -> None:
        super().__init__()
        self.reader = reader


async def session_handler(iface: WireInterface, sid: int) -> None:
    reader = None
    ctx = Context(iface, sid)
    while True:
        try:
            # wait for new message, if needed, and find handler
            if not reader:
                reader = ctx.make_reader()
                await reader.aopen()
            try:
                handler, args = workflow_handlers[reader.type]
            except KeyError:
                handler, args = unexpected_msg, ()

            m = utils.unimport_begin()
            w = handler(ctx, reader, *args)
            try:
                workflow.onstart(w)
                await w
            finally:
                workflow.onclose(w)
                utils.unimport_end(m)

        except UnexpectedMessageError as exc:
            # retry with opened reader from the exception
            reader = exc.reader
            continue
        except Error as exc:
            # we log wire.Error as warning, not as exception
            if __debug__:
                log.warning(__name__, "failure: %s", exc.message)
        except Exception as exc:
            # sessions are never closed by raised exceptions
            if __debug__:
                log.exception(__name__, exc)

        # read new message in next iteration
        reader = None


async def protobuf_workflow(
    ctx: Context, reader: codec_v1.Reader, handler: Handler, *args: Any
) -> None:
    from trezor.messages.Failure import Failure

    req = await protobuf.load_message(reader, messages.get_type(reader.type))

    if __debug__:
        log.debug(__name__, "%s:%x request: %s", ctx.iface.iface_num(), ctx.sid, req)

    try:
        res = await handler(ctx, req, *args)
    except UnexpectedMessageError:
        # session handler takes care of this one
        raise
    except Error as exc:
        # respond with specific code and message
        await ctx.write(Failure(code=exc.code, message=exc.message))
        raise
    except Exception as e:
        # respond with a generic code and message
        message = "Firmware error"
        if __debug__:
            message = "{}: {}".format(type(e), e)
        await ctx.write(Failure(code=FailureType.FirmwareError, message=message))
        raise
    if res:
        # respond with a specific response
        await ctx.write(res)


async def keychain_workflow(
    ctx: Context,
    req: protobuf.MessageType,
    namespace: List,
    handler: Handler,
    *args: Any
) -> Any:
    from apps.common import seed

    keychain = await seed.get_keychain(ctx, namespace)
    args += (keychain,)
    try:
        return await handler(ctx, req, *args)
    finally:
        keychain.__del__()


def import_workflow(
    ctx: Context, req: protobuf.MessageType, pkgname: str, modname: str, *args: Any
) -> Any:
    modpath = "%s.%s" % (pkgname, modname)
    module = __import__(modpath, None, None, (modname,), 0)  # type: ignore
    handler = getattr(module, modname)
    return handler(ctx, req, *args)


async def unexpected_msg(ctx: Context, reader: codec_v1.Reader) -> None:
    from trezor.messages.Failure import Failure

    # receive the message and throw it away
    await read_full_msg(reader)

    # respond with an unknown message error
    await ctx.write(
        Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")
    )


async def read_full_msg(reader: codec_v1.Reader) -> None:
    while reader.size > 0:
        buf = bytearray(reader.size)
        await reader.areadinto(buf)
