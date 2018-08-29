import protobuf
from trezor import log, loop, messages, utils, workflow
from trezor.wire import codec_v1
from trezor.wire.errors import *

workflow_handlers = {}


def add(mtype, pkgname, modname, *args):
    """Shortcut for registering a dynamically-imported Protobuf workflow."""
    register(mtype, protobuf_workflow, import_workflow, pkgname, modname, *args)


def register(mtype, handler, *args):
    """Register `handler` to get scheduled after `mtype` message is received."""
    if isinstance(mtype, type) and issubclass(mtype, protobuf.MessageType):
        mtype = mtype.MESSAGE_WIRE_TYPE
    if mtype in workflow_handlers:
        raise KeyError
    workflow_handlers[mtype] = (handler, args)


def setup(iface):
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(session_handler(iface, codec_v1.SESSION_ID))


class Context:
    def __init__(self, iface, sid):
        self.iface = iface
        self.sid = sid

    async def call(self, msg, *types):
        """
        Reply with `msg` and wait for one of `types`. See `self.write()` and
        `self.read()`.
        """
        await self.write(msg)
        return await self.read(types)

    async def read(self, types):
        """
        Wait for incoming message on this wire context and return it.  Raises
        `UnexpectedMessageError` if the message type does not match one of
        `types`; and caller should always make sure to re-raise it.
        """
        reader = self.getreader()

        if __debug__:
            log.debug(
                __name__, "%s:%x read: %s", self.iface.iface_num(), self.sid, types
            )

        await reader.aopen()  # wait for the message header

        # if we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it
        if reader.type not in types:
            raise UnexpectedMessageError(reader)

        # look up the protobuf class and parse the message
        pbtype = messages.get_type(reader.type)
        return await protobuf.load_message(reader, pbtype)

    async def write(self, msg):
        """
        Write a protobuf message to this wire context.
        """
        writer = self.getwriter()

        if __debug__:
            log.debug(
                __name__, "%s:%x write: %s", self.iface.iface_num(), self.sid, msg
            )

        # get the message size
        counter = protobuf.CountingWriter()
        await protobuf.dump_message(counter, msg)

        # write the message
        writer.setheader(msg.MESSAGE_WIRE_TYPE, counter.size)
        await protobuf.dump_message(writer, msg)
        await writer.aclose()

    def wait(self, *tasks):
        """
        Wait until one of the passed tasks finishes, and return the result,
        while servicing the wire context.  If a message comes until one of the
        tasks ends, `UnexpectedMessageError` is raised.
        """
        return loop.spawn(self.read(()), *tasks)

    def getreader(self):
        return codec_v1.Reader(self.iface)

    def getwriter(self):
        return codec_v1.Writer(self.iface)


class UnexpectedMessageError(Exception):
    def __init__(self, reader):
        super().__init__()
        self.reader = reader


async def session_handler(iface, sid):
    reader = None
    ctx = Context(iface, sid)
    while True:
        try:
            # wait for new message, if needed, and find handler
            if not reader:
                reader = ctx.getreader()
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
            log.warning(__name__, "failure: %s", exc.message)
        except Exception as exc:
            # sessions are never closed by raised exceptions
            log.exception(__name__, exc)

        # read new message in next iteration
        reader = None


async def protobuf_workflow(ctx, reader, handler, *args):
    from trezor.messages.Failure import Failure

    req = await protobuf.load_message(reader, messages.get_type(reader.type))
    try:
        res = await handler(ctx, req, *args)
    except UnexpectedMessageError:
        # session handler takes care of this one
        raise
    except Error as exc:
        # respond with specific code and message
        await ctx.write(Failure(code=exc.code, message=exc.message))
        raise
    except Exception as exc:
        # respond with a generic code and message
        await ctx.write(
            Failure(code=FailureType.FirmwareError, message="Firmware error")
        )
        raise
    if res:
        # respond with a specific response
        await ctx.write(res)


def import_workflow(ctx, req, pkgname, modname, *args):
    modpath = "%s.%s" % (pkgname, modname)
    module = __import__(modpath, None, None, (modname,), 0)
    handler = getattr(module, modname)
    return handler(ctx, req, *args)


async def unexpected_msg(ctx, reader):
    from trezor.messages.Failure import Failure

    # receive the message and throw it away
    while reader.size > 0:
        buf = bytearray(reader.size)
        await reader.areadinto(buf)

    # respond with an unknown message error
    await ctx.write(
        Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")
    )
