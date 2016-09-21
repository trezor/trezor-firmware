from protobuf.protobuf import build_protobuf_message

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

_session_handlers = {}  # session id -> generator
_workflow_genfuncs = {}  # wire type -> (generator function, args)
_opened_sessions = set()  # session ids


def generate_session_id():
    while True:
        session_id = random.uniform(0x0fffffff) + 1
        if session_id not in _opened_sessions:
            return session_id


def open_session():
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
    log.info(__name__, 'registering %s for type %d',
             (genfunc, args), wire_type)
    _workflow_genfuncs[wire_type] = (genfunc, args)


def register_session(session_id, handler):
    if session_id not in _opened_sessions:
        raise KeyError('session %d is unknown' % session_id)
    if session_id in _session_handlers:
        raise KeyError('session %d is already registered' % session_id)
    log.info(__name__, 'registering %s for session %d', handler, session_id)
    _session_handlers[session_id] = handler


def setup():
    report_writer = write_report_stream()
    report_writer.send(None)

    open_session_handler = _handle_open_session(report_writer)
    open_session_handler.send(None)

    close_session_handler = _handle_close_session(report_writer)
    close_session_handler.send(None)

    fallback_session_handler = _handle_unknown_session()
    fallback_session_handler.send(None)

    session_dispatcher = dispatch_reports_by_session(
        _session_handlers,
        open_session_handler,
        close_session_handler,
        fallback_session_handler)
    session_dispatcher.send(None)

    schedule_task(read_report_stream(session_dispatcher))


async def read_message(session_id, *exp_types):
    future = Future()
    wire_decoder = decode_wire_stream(
        _dispatch_and_build_protobuf, session_id, exp_types, future)
    wire_decoder.send(None)
    register_session(session_id, wire_decoder)
    return await future


async def write_message(session_id, pbuf_message):
    msg_data = await pbuf_message.dumps()
    msg_type = pbuf_message.message_type.wire_type
    writer = write_report_stream()
    writer.send(None)
    encode_wire_message(msg_type, msg_data, session_id, writer)


def protobuf_handler(msg_type, data_len, session_id, callback, *args):
    def finalizer(message):
        start_workflow(callback(message, session_id, *args))
    pbuf_type = get_protobuf_type(msg_type)
    builder = build_protobuf_message(pbuf_type, finalizer)
    builder.send(None)
    return pbuf_type.load(builder)


def _handle_open_session(write_target):
    while True:
        yield
        session_id = open_session()
        wire_decoder = decode_wire_stream(_handle_registered_type, session_id)
        wire_decoder.send(None)
        register_session(session_id, wire_decoder)
        encode_session_open_message(session_id, write_target)


def _handle_close_session(write_target):
    while True:
        session_id = yield
        close_session(session_id)
        encode_session_close_message(session_id, write_target)


def _handle_unknown_session():
    while True:
        yield  # TODO


class UnexpectedMessageError(Exception):
    pass


def _dispatch_and_build_protobuf(msg_type, data_len, session_id, exp_types, future):
    if msg_type in exp_types:
        pbuf_type = get_protobuf_type(msg_type)
        builder = build_protobuf_message(pbuf_type, future.resolve)
        builder.send(None)
        return pbuf_type.load(builder)
    else:
        future.resolve(UnexpectedMessageError(msg_type))
        return _handle_registered_type(msg_type, data_len, session_id)


def _handle_registered_type(msg_type, data_len, session_id):
    genfunc, args = _workflow_genfuncs.get(
        msg_type, (_handle_unexpected_type, ()))
    return genfunc(msg_type, data_len, session_id, *args)


def _handle_unexpected_type(msg_type, data_len, session_id):
    log.info(__name__, 'skipping message %d of len %d' % (msg_type, data_len))
    try:
        while True:
            yield
    except EOFError:
        pass
