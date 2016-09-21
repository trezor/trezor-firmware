from trezor import log
from .wire_codec import parse_report, REP_MARKER_OPEN, REP_MARKER_CLOSE


def dispatch_reports_by_session(handlers,
                                open_handler,
                                close_handler,
                                fallback_handler):
    '''
    Consumes reports adhering to the wire codec and dispatches the report
    payloads by between the passed handlers.
    '''

    while True:
        marker, session_id, report_data = parse_report((yield))

        if marker == REP_MARKER_OPEN:
            log.debug(__name__, 'request for new session')
            open_handler.send(session_id)
            continue

        elif marker == REP_MARKER_CLOSE:
            log.debug(__name__, 'request for closing session %d', session_id)
            close_handler.send(session_id)
            continue

        elif session_id in handlers:
            log.debug(__name__, 'report on session %d', session_id)
            handler = handlers[session_id]

        else:
            log.debug(__name__, 'report on unknown session %d', session_id)
            handler = fallback_handler

        try:
            handler.send(report_data)
        except StopIteration:
            handlers.pop(session_id)
        except Exception as e:
            log.exception(__name__, e)
