from protobuf import build_protobuf_message

from trezor.loop import schedule_task, Future
from trezor.crypto import random
from trezor.messages import get_protobuf_type
from trezor.workflow import start_workflow
from trezor import log

from .wire_io import read_report_stream, write_report_stream
from .wire_dispatcher import dispatch_reports_by_session
from .wire_codec import \
    decode_wire_stream, encode_wire_message, \
    encode_session_open_message, encode_session_close_message
from .wire_codec_v1 import \
    SESSION_V1, \
    decode_wire_v1_stream, \
    encode_wire_v1_message

_session_handlers = {}  # session id -> generator
_workflow_genfuncs = {}  # wire type -> (generator function, args)
_opened_sessions = set()  # session ids

# TODO: get rid of this, use callbacks instead
report_writer = write_report_stream()
report_writer.send(None)


def generate_session_id():
    while True:
        session_id = random.uniform(0xffffffff) + 1
        if session_id not in _opened_sessions:
            return session_id


def open_session(session_id=None):
    if session_id is None:
        session_id = generate_session_id()
    _opened_sessions.add(session_id)
    log.info(__name__, 'opened session %d: %s', session_id, _opened_sessions)
    return session_id


def close_session(session_id):
    _opened_sessions.discard(session_id)
    _session_handlers.pop(session_id, None)
    log.info(__name__, 'closed session %d: %s', session_id, _opened_sessions)


def register_type(wire_type, genfunc, *args):
    if wire_type in _workflow_genfuncs:
        raise KeyError('message of type %d already registered' % wire_type)
    log.info(__name__, 'registering message type %d', wire_type)
    _workflow_genfuncs[wire_type] = (genfunc, args)


def register_session(session_id, handler):
    if session_id not in _opened_sessions:
        raise KeyError('session %d is unknown' % session_id)
    if session_id in _session_handlers:
        raise KeyError('session %d is already being listened on' % session_id)
    log.info(__name__, 'listening on session %d', session_id)
    _session_handlers[session_id] = handler


def setup():
    session_dispatcher = dispatch_reports_by_session(
        _session_handlers,
        _handle_open_session,
        _handle_close_session,
        _handle_unknown_session)
    session_dispatcher.send(None)
    schedule_task(read_report_stream(session_dispatcher))

    v1_handler = decode_wire_v1_stream(_handle_registered_type, SESSION_V1)
    v1_handler.send(None)
    open_session(SESSION_V1)
    register_session(SESSION_V1, v1_handler)


async def read_message(session_id, *exp_types):
    log.info(__name__, 'reading message of types %s', exp_types)
    future = Future()
    wire_decoder = decode_wire_stream(
        _dispatch_and_build_protobuf, session_id, exp_types, future)
    wire_decoder.send(None)
    register_session(session_id, wire_decoder)
    return await future


async def write_message(session_id, pbuf_message):
    log.info(__name__, 'writing message %s', pbuf_message)
    msg_data = await pbuf_message.dumps()
    msg_type = pbuf_message.message_type.wire_type

    if session_id == SESSION_V1:
        encode_wire_v1_message(msg_type, msg_data, report_writer)
    else:
        encode_wire_message(msg_type, msg_data, session_id, report_writer)


async def reply_message(session_id, pbuf_message, *exp_types):
    await write_message(session_id, pbuf_message)
    return await read_message(session_id, *exp_types)


class FailureError(Exception):

    def __init__(self, code, message):
        super(FailureError, self).__init__(code, message)

    def to_protobuf(self):
        from trezor.messages.Failure import Failure
        return Failure(code=self.args[0],
                       message=self.args[1])


async def monitor_workflow(workflow, session_id):
    try:
        result = await workflow

    except FailureError as e:
        await write_message(session_id, e.to_protobuf())
        raise

    except Exception as e:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import FirmwareError
        await write_message(session_id,
                            Failure(code=FirmwareError,
                                    message='Firmware Error'))
        raise

    else:
        if result is not None:
            await write_message(session_id, result)
        return result

    finally:
        if session_id in _opened_sessions:
            if session_id == SESSION_V1:
                wire_decoder = decode_wire_v1_stream(_handle_registered_type,
                                                     SESSION_V1)
            else:
                wire_decoder = decode_wire_stream(
                    _handle_registered_type, session_id)
            wire_decoder.send(None)
            register_session(session_id, wire_decoder)


def protobuf_handler(msg_type, data_len, session_id, callback, *args):
    def finalizer(message):
        workflow = callback(message, session_id, *args)
        monitored = monitor_workflow(workflow, session_id)
        start_workflow(monitored)
    pbuf_type = get_protobuf_type(msg_type)
    builder = build_protobuf_message(pbuf_type, finalizer)
    builder.send(None)
    return pbuf_type.load(builder)


def _handle_open_session():
    session_id = open_session()
    wire_decoder = decode_wire_stream(_handle_registered_type, session_id)
    wire_decoder.send(None)
    register_session(session_id, wire_decoder)
    encode_session_open_message(session_id, report_writer)


def _handle_close_session(session_id):
    close_session(session_id)
    encode_session_close_message(session_id, report_writer)


def _handle_unknown_session(session_id, report_data):
    pass  # TODO


def _dispatch_and_build_protobuf(msg_type, data_len, session_id, exp_types, future):
    if msg_type in exp_types:
        pbuf_type = get_protobuf_type(msg_type)
        builder = build_protobuf_message(pbuf_type, future.resolve)
        builder.send(None)
        return pbuf_type.load(builder)
    else:
        from trezor.messages.FailureType import UnexpectedMessage
        future.resolve(FailureError(UnexpectedMessage, 'Unexpected message'))
        return _handle_registered_type(msg_type, data_len, session_id)


def _handle_registered_type(msg_type, data_len, session_id):
    fallback = (_handle_unexpected_type, ())
    genfunc, args = _workflow_genfuncs.get(msg_type, fallback)
    return genfunc(msg_type, data_len, session_id, *args)


def _handle_unexpected_type(msg_type, data_len, session_id):
    log.info(__name__, 'skipping message %d of len %d on session %d' %
             (msg_type, data_len, session_id))
    try:
        while True:
            yield
    except EOFError:
        pass
