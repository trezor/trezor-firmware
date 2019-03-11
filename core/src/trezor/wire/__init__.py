import protobuf
from trezor import log, loop, messages, utils, workflow
from trezor.messages import FailureType
from trezor.messages.Failure import Failure
from trezor.wire import codec_v1
from trezor.wire.errors import Error

# import all errors into namespace, so that `wire.Error` is available elsewhere
from trezor.wire.errors import *  # isort:skip # noqa: F401,F403


workflow_handlers = {}
workflow_namespaces = {}


def add(mtype, pkgname, modname, namespace=None):
    """Shortcut for registering a dynamically-imported Protobuf workflow."""
    if namespace is not None:
        register(mtype, keychain_workflow, namespace, import_workflow, pkgname, modname)
    else:
        register(mtype, import_workflow, pkgname, modname)


def register(mtype, handler, *args):
    """Register `handler` to get scheduled after `mtype` message is received."""
    if isinstance(mtype, type) and issubclass(mtype, protobuf.MessageType):
        mtype = mtype.MESSAGE_WIRE_TYPE
    if mtype in workflow_handlers:
        raise KeyError
    workflow_handlers[mtype] = (handler, args)


def setup(iface):
    """Initialize the wire stack on passed USB interface."""
    loop.schedule(handle_session(iface, codec_v1.SESSION_ID))


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
        del msg
        return await self.read(types)

    async def read(self, types):
        """
        Wait for incoming message on this wire context and return it.  Raises
        `UnexpectedMessageError` if the message type does not match one of
        `types`; and caller should always make sure to re-raise it.
        """
        if __debug__:
            log.debug(
                __name__, "%s:%x read: %s", self.iface.iface_num(), self.sid, types
            )

        msg = await codec_v1.read_message(self.iface, _message_buffer)

        # if we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it
        if msg.type not in types:
            raise UnexpectedMessageError(msg)

        # look up the protobuf class and parse the message
        pbtype = messages.get_type(msg.type)

        return protobuf.load_message(msg, pbtype)

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
        fields = msg.get_fields()
        size = protobuf.count_message(msg, fields)

        # write the message
        writer.setheader(msg.MESSAGE_WIRE_TYPE, size)
        protobuf.dump_message(writer, msg, fields)
        await writer.aclose()

    def wait(self, *tasks):
        """
        Wait until one of the passed tasks finishes, and return the result,
        while servicing the wire context.  If a message comes until one of the
        tasks ends, `UnexpectedMessageError` is raised.
        """
        return loop.spawn(self.read(()), *tasks)


class UnexpectedMessageError(Exception):
    def __init__(self, msg):
        self.msg = msg


async def handle_session(iface, sid):
    ctx = Context(iface, sid)
    while True:
        try:
            mods = utils.unimport_begin()
            try:
                req = await ctx.read(workflow_handlers)
            except UnexpectedMessage:
                res = unexpected_message()
            else:
                res = await handle_request(ctx, req)
            if res is not None:
                await ctx.write(res)
            req = None
            res = None
            utils.unimport_end(mods)
        except Exception as exc:
            if __debug__:
                log.exception(__name__, exc)


async def handle_request(ctx, request):
    handler = get_workflow_handler(request)
    try:
        workflow.onstart(handler)

        response = None
        try:
            response = await handler

        except Error as exc:
            if __debug__:
                log.warning(__name__, exc)
            response = failure(exc.code, exc.message)

        except Exception:
            if __debug__:
                log.exception(__name__, exc)
            response = failure()

    finally:
        workflow.onclose(handler)

    return response


async def keychain_workflow(ctx, req, namespace, handler, *args):
    from apps.common import seed

    keychain = await seed.get_keychain(ctx, namespace)
    args += (keychain,)
    try:
        return await handler(ctx, req, *args)
    finally:
        keychain.__del__()


def get_workflow_handler(request):
    record = workflow_handlers[request.MESSAGE_WIRE_TYPE]
    if isinstance(record, tuple):
        pkgname, modname = record
        record = import_workflow(pkgname, modname)
    return record(ctx, request)


def import_workflow(pkgname, modname):
    modpath = "%s.%s" % (pkgname, modname)
    module = __import__(modpath, None, None, (modname,), 0)
    handler = getattr(module, modname)
    return handler


def failure(code=FailureType.FirmwareError, message="Firmware error"):
    return Failure(code=code, message=message)


def unexpected_message():
    return Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")
