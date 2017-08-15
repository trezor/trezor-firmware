import protobuf

from trezor import log
from trezor import loop
from trezor import messages
from trezor import workflow

from . import codec_v1
from . import codec_v2

workflow_handlers = {}


def register(mtype, handler, *args):
    '''Register `handler` to get scheduled after `mtype` message is received.'''
    if mtype in workflow_handlers:
        raise KeyError
    workflow_handlers[mtype] = (handler, args)


def setup(iface):
    '''Initialize the wire stack on passed USB interface.'''
    session_supervisor = codec_v2.SesssionSupervisor(iface, session_handler)
    session_supervisor.open(codec_v1.SESSION_ID)
    loop.schedule_task(session_supervisor.listen())


class Context:
    def __init__(self, iface, sid):
        self.iface = iface
        self.sid = sid

    async def call(self, msg, *types):
        '''
        Reply with `msg` and wait for one of `types`. See `self.write()` and
        `self.read()`.
        '''
        await self.write(msg)
        return await self.read(types)

    async def read(self, types):
        '''
        Wait for incoming message on this wire context and return it.  Raises
        `UnexpectedMessageError` if the message type does not match one of
        `types`; and caller should always make sure to re-raise it.
        '''
        reader = self.getreader()

        await reader.aopen()  # wait for the message header

        # if we got a message with unexpected type, raise the reader via
        # `UnexpectedMessageError` and let the session handler deal with it
        if reader.type not in types:
            raise UnexpectedMessageError(reader)

        # look up the protobuf class and parse the message
        pbtype = messages.get_type(reader.type)
        return await protobuf.load_message(reader, pbtype)

    async def write(self, msg):
        '''
        Write a protobuf message to this wire context.
        '''
        writer = self.getwriter()

        # get the message size
        counter = protobuf.CountingWriter()
        await protobuf.dump_message(counter, msg)

        # write the message
        writer.setheader(msg.MESSAGE_WIRE_TYPE, counter.size)
        await protobuf.dump_message(writer, msg)
        await writer.aclose()

    def getreader(self):
        if self.sid == codec_v1.SESSION_ID:
            return codec_v1.Reader(self.iface)
        else:
            return codec_v2.Reader(self.iface, self.sid)

    def getwriter(self):
        if self.sid == codec_v1.SESSION_ID:
            return codec_v1.Writer(self.iface)
        else:
            return codec_v2.Writer(self.iface, self.sid)


class UnexpectedMessageError(Exception):
    def __init__(self, reader):
        super().__init__()
        self.reader = reader


class FailureError(Exception):
    def __init__(self, code, message):
        super().__init__()
        self.code = code
        self.message = message


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

            await handler(ctx, reader, *args)

        except UnexpectedMessageError as exc:
            # retry with opened reader from the exception
            reader = exc.reader
            continue
        except FailureError as exc:
            # we log FailureError as warning, not as exception
            log.warning(__name__, 'failure: %s', exc.message)
        except Exception as exc:
            # sessions are never closed by raised exceptions
            log.exception(__name__, exc)

        # read new message in next iteration
        reader = None


async def protobuf_workflow(ctx, reader, handler, *args):
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import FirmwareError

    req = await protobuf.load_message(reader, messages.get_type(reader.type))
    try:
        res = await handler(ctx, req, *args)
    except UnexpectedMessageError:
        # session handler takes care of this one
        raise
    except FailureError as exc:
        # respond with specific code and message
        await ctx.write(Failure(code=exc.code, message=exc.message))
        raise
    except Exception as exc:
        # respond with a generic code and message
        await ctx.write(Failure(code=FirmwareError, message='Firmware error'))
        raise
    if res:
        # respond with a specific response
        await ctx.write(res)


async def unexpected_msg(ctx, reader):
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import UnexpectedMessage

    # receive the message and throw it away
    while reader.size > 0:
        buf = bytearray(reader.size)
        await reader.areadinto(buf)

    # respond with an unknown message error
    await ctx.write(
        Failure(code=UnexpectedMessage, message='Unexpected message'))
