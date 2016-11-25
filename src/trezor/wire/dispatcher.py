from trezor import log
from .codec import parse_report, REP_MARKER_OPEN, REP_MARKER_CLOSE
from .codec_v1 import detect_v1, parse_report_v1


def dispatch_reports_by_session(handlers,
                                open_callback,
                                close_callback,
                                unknown_callback):
    '''
    Consumes reports adhering to the wire codec and dispatches the report
    payloads by between the passed handlers.
    '''

    while True:

        data = (yield)
        if detect_v1(data):
            marker, session_id, report_data = parse_report_v1(data)
        else:
            marker, session_id, report_data = parse_report(data)

        if marker == REP_MARKER_OPEN:
            log.debug(__name__, 'request for new session')
            open_callback()
            continue

        elif marker == REP_MARKER_CLOSE:
            log.debug(__name__, 'request for closing session %d', session_id)
            close_callback(session_id)
            continue

        elif session_id not in handlers:
            log.debug(__name__, 'report on unknown session %d', session_id)
            unknown_callback(session_id, report_data)
            continue

        log.debug(__name__, 'report on session %d', session_id)
        handler = handlers[session_id]

        try:
            handler.send(report_data)
        except StopIteration:
            handlers.pop(session_id)
        except Exception as e:
            log.exception(__name__, e)
