import ubinascii
import protobuf

from trezor import log
from trezor import loop
from trezor import messages
from trezor import msg
from trezor import workflow

from . import codec_v1
from . import codec_v2
from . import sessions

_interface = None

_workflow_callbacks = {}  # wire type -> function returning workflow
_workflow_args = {}  # wire type -> args


def register(wire_type, callback, *args):
    if wire_type in _workflow_callbacks:
        raise KeyError('Message %d already registered' % wire_type)
    _workflow_callbacks[wire_type] = callback
    _workflow_args[wire_type] = args


def setup(iface):
    global _interface

    # setup wire interface for reading and writing
    _interface = iface

    # implicitly register v1 codec on its session.  v2 sessions are
    # opened/closed explicitely through session control messages.
    _session_open(codec_v1.SESSION)

    # run session dispatcher
    loop.schedule_task(_dispatch_reports())


async def read(session_id, *wire_types):
    log.info(__name__, 'session %x: read(%s)', session_id, wire_types)
    signal = loop.Signal()
    sessions.listen(session_id, _handle_response, wire_types, signal)
    return await signal


async def write(session_id, pbuf_msg):
    log.info(__name__, 'session %x: write(%s)', session_id, pbuf_msg)
    pbuf_type = pbuf_msg.__class__
    msg_data = pbuf_type.dumps(pbuf_msg)
    msg_type = pbuf_type.MESSAGE_WIRE_TYPE
    sessions.get_codec(session_id).encode(
        session_id, msg_type, msg_data, _write_report)


async def call(session_id, pbuf_msg, *response_types):
    await write(session_id, pbuf_msg)
    return await read(session_id, *response_types)


class FailureError(Exception):

    def to_protobuf(self):
        from trezor.messages.Failure import Failure
        code, message = self.args
        return Failure(code=code, message=message)


class CloseWorkflow(Exception):
    pass


def protobuf_workflow(session_id, msg_type, data_len, callback, *args):
    return _build_protobuf(msg_type, _start_protobuf_workflow, session_id, callback, args)


def _start_protobuf_workflow(pbuf_msg, session_id, callback, args):
    wf = callback(session_id, pbuf_msg, *args)
    wf = _wrap_protobuf_workflow(wf, session_id)
    workflow.start(wf)


async def _wrap_protobuf_workflow(wf, session_id):
    try:
        result = await wf

    except CloseWorkflow:
        return

    except FailureError as e:
        await write(session_id, e.to_protobuf())
        raise

    except Exception as e:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import FirmwareError
        await write(session_id, Failure(
            code=FirmwareError, message='Firmware Error'))
        raise

    else:
        if result is not None:
            await write(session_id, result)
        return result

    finally:
        if session_id in sessions.opened:
            sessions.listen(session_id, _handle_workflow)


def _build_protobuf(msg_type, callback, *args):
    pbuf_type = messages.get_protobuf_type(msg_type)
    builder = protobuf.build_message(pbuf_type, callback, *args)
    builder.send(None)
    return pbuf_type.load(target=builder)


def _handle_response(session_id, msg_type, data_len, response_types, signal):
    if msg_type in response_types:
        return _build_protobuf(msg_type, signal.send)
    else:
        signal.send(CloseWorkflow())
        return _handle_workflow(session_id, msg_type, data_len)


def _handle_workflow(session_id, msg_type, data_len):
    if msg_type in _workflow_callbacks:
        callback = _workflow_callbacks[msg_type]
        args = _workflow_args[msg_type]
        return callback(session_id, msg_type, data_len, *args)
    else:
        return _handle_unexpected(session_id, msg_type, data_len)


def _handle_unexpected(session_id, msg_type, data_len):
    log.warning(
        __name__, 'session %x: skip type %d, len %d', session_id, msg_type, data_len)

    # read the message in full
    try:
        while True:
            yield
    except EOFError:
        pass

    # respond with an unknown message error
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import UnexpectedMessage
    failure = Failure(code=UnexpectedMessage, message='Unexpected message')
    failure = Failure.dumps(failure)
    sessions.get_codec(session_id).encode(
        session_id, Failure.MESSAGE_WIRE_TYPE, failure, _write_report)


def _write_report(report):
    # if __debug__:
    #     log.debug(__name__, 'write report %s', ubinascii.hexlify(report))
    msg.send(_interface, report)


def _dispatch_reports():
    while True:
        report, = yield loop.Select(_interface)
        report = memoryview(report)
        # if __debug__:
        #     log.debug(__name__, 'read report %s', ubinascii.hexlify(report))
        sessions.dispatch(
            report, _session_open, _session_close, _session_unknown)


def _session_open(session_id=None):
    session_id = sessions.open(session_id)
    sessions.listen(session_id, _handle_workflow)
    sessions.get_codec(session_id).encode_session_open(
        session_id, _write_report)


def _session_close(session_id):
    sessions.close(session_id)
    sessions.get_codec(session_id).encode_session_close(
        session_id, _write_report)


def _session_unknown(session_id, report_data):
    log.warning(__name__, 'report on unknown session %x', session_id)
