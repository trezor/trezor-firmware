import protobuf

from trezor import log
from trezor import loop
from trezor import messages
from trezor import workflow

from . import codec_v1
from . import codec_v2

workflows = {}


def register(wire_type, handler, *args):
    if wire_type in workflows:
        raise KeyError
    workflows[wire_type] = (handler, args)


def setup(interface):
    session_supervisor = codec_v2.SesssionSupervisor(interface,
                                                     session_handler)
    session_supervisor.open(codec_v1.SESSION_ID)
    loop.schedule_task(session_supervisor.listen())


class Context:
    def __init__(self, interface, session_id):
        self.interface = interface
        self.session_id = session_id

    def get_reader(self):
        if self.session_id == codec_v1.SESSION_ID:
            return codec_v1.Reader(self.interface)
        else:
            return codec_v2.Reader(self.interface, self.session_id)

    def get_writer(self, mtype, msize):
        if self.session_id == codec_v1.SESSION_ID:
            return codec_v1.Writer(self.interface, mtype, msize)
        else:
            return codec_v2.Writer(self.interface, self.session_id, mtype, msize)

    async def read(self, types):
        reader = self.get_reader()
        await reader.open()
        if reader.type not in types:
            raise UnexpectedMessageError(reader)
        return await protobuf.load_message(reader,
                                           messages.get_type(reader.type))

    async def write(self, msg):
        counter = protobuf.CountingWriter()
        await protobuf.dump_message(counter, msg)
        writer = self.get_writer(msg.MESSAGE_WIRE_TYPE, counter.size)
        await protobuf.dump_message(writer, msg)
        await writer.close()

    async def call(self, msg, types):
        await self.write(msg)
        return await self.read(types)


class UnexpectedMessageError(Exception):
    def __init__(self, reader):
        super().__init__()
        self.reader = reader


class FailureError(Exception):
    def __init__(self, code, message):
        super().__init__()
        self.code = code
        self.message = message


class Workflow:
    def __init__(self, default):
        self.handlers = {}
        self.default = default

    async def __call__(self, interface, session_id):
        ctx = Context(interface, session_id)
        while True:
            try:
                reader = ctx.get_reader()
                await reader.open()
                try:
                    handler = self.handlers[reader.type]
                except KeyError:
                    handler = self.default
                try:
                    await handler(ctx, reader)
                except UnexpectedMessageError as unexp_msg:
                    reader = unexp_msg.reader
            except Exception as e:
                log.exception(__name__, e)


async def protobuf_workflow(ctx, reader, handler, *args):
    msg = await protobuf.load_message(reader, messages.get_type(reader.type))
    try:
        res = await handler(reader.sid, msg, *args)
    except Exception as exc:
        if not isinstance(exc, UnexpectedMessageError):
            await ctx.write(make_failure_msg(exc))
        raise
    else:
        if res:
            await ctx.write(res)


async def handle_unexp_msg(ctx, reader):
    # receive the message and throw it away
    while reader.size > 0:
        buf = bytearray(reader.size)
        await reader.readinto(buf)
    # respond with an unknown message error
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import UnexpectedMessage
    await ctx.write(
        Failure(code=UnexpectedMessage, message='Unexpected message'))

def make_failure_msg(exc):
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import FirmwareError
    if isinstance(exc, FailureError):
        code = exc.code
        message = exc.message
    else:
        code = FirmwareError
        message = 'Firmware Error'
    return Failure(code=code, message=message)
