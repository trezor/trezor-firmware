from trezor import log
from trezor.crypto import random

from . import codec_v1
from . import codec_v2

opened = set()  # opened session ids
readers = {}  # session id -> generator


def generate():
    while True:
        session_id = random.uniform(0xffffffff) + 1
        if session_id not in opened:
            return session_id


def open(session_id=None):
    if session_id is None:
        session_id = generate()
    log.info(__name__, 'session %d: open', session_id)
    opened.add(session_id)
    return session_id


def close(session_id):
    log.info(__name__, 'session %d: close', session_id)
    opened.discard(session_id)
    readers.pop(session_id, None)


def get_codec(session_id):
    if session_id == codec_v1.SESSION:
        return codec_v1
    else:
        return codec_v2


def listen(session_id, handler, *args):
    if session_id not in opened:
        raise KeyError('Session %d is unknown' % session_id)
    if session_id in readers:
        raise KeyError('Session %d is already being listened on' % session_id)
    log.info(__name__, 'session %d: listening', session_id)
    decoder = get_codec(session_id).decode_stream(session_id, handler, *args)
    decoder.send(None)
    readers[session_id] = decoder


def dispatch(report, open_callback, close_callback, unknown_callback):
    '''
    Dispatches payloads of reports adhering to one of the wire codecs.
    '''

    if codec_v1.detect(report):
        marker, session_id, report_data = codec_v1.parse_report(report)
    else:
        marker, session_id, report_data = codec_v2.parse_report(report)

        if marker == codec_v2.REP_MARKER_OPEN:
            log.debug(__name__, 'request for new session')
            open_callback()
            return
        elif marker == codec_v2.REP_MARKER_CLOSE:
            log.debug(__name__, 'request for closing session %d', session_id)
            close_callback(session_id)
            return

    if session_id not in readers:
        log.warning(__name__, 'report on unknown session %d', session_id)
        unknown_callback(session_id, report_data)
        return

    log.debug(__name__, 'report on session %d', session_id)
    reader = readers[session_id]

    try:
        reader.send(report_data)
    except StopIteration:
        readers.pop(session_id)
    except Exception as e:
        log.exception(__name__, e)
