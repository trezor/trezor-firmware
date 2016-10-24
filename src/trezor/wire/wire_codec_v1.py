from micropython import const
import ustruct

SESSION_V1 = const(0)
REP_MARKER_V1 = const(63)  # ord('?')
REP_MARKER_V1_LEN = const(1)  # len('?')

_REP_LEN = const(64)
_MSG_HEADER_MAGIC = const(35)  # org('#')
_MSG_HEADER_V1 = '>BBHL'  # magic, magic, wire type, data length
_MSG_HEADER_V1_LEN = ustruct.calcsize(_MSG_HEADER_V1)


def detect_v1(data):
    return (data[0] == REP_MARKER_V1)


def parse_report_v1(data):
    if len(data) != _REP_LEN:
        raise ValueError('Invalid buffer size')
    return None, SESSION_V1, data[1:]


def parse_message(data):
    magic1, magic2, msg_type, data_len = ustruct.unpack(_MSG_HEADER_V1, data)
    if magic1 != _MSG_HEADER_MAGIC or magic2 != _MSG_HEADER_MAGIC:
        raise ValueError('Corrupted magic bytes')
    return msg_type, data_len, data[_MSG_HEADER_V1_LEN:]


def serialize_message_header(data, msg_type, msg_len):
    if len(data) < REP_MARKER_V1_LEN + _MSG_HEADER_V1_LEN:
        raise ValueError('Invalid buffer size')
    if msg_type < 0 or msg_type > 65535:
        raise ValueError('Value is out of range')
    ustruct.pack_into(
        _MSG_HEADER_V1, data, REP_MARKER_V1_LEN,
        _MSG_HEADER_MAGIC, _MSG_HEADER_MAGIC, msg_type, msg_len)


def decode_wire_v1_stream(genfunc, session_id, *args):
    '''Decode a v1 wire message from the report data and stream it to target.

Receives report payloads.  After first report, creates target by calling
`genfunc(msg_type, data_len, session_id, *args)` and sends chunks of message
data.
Throws `EOFError` to target after last data chunk.

Pass report payloads as `memoryview` for cheaper slicing.
'''

    message = yield  # read first report
    msg_type, data_len, data = parse_message(message)

    target = genfunc(msg_type, data_len, session_id, *args)
    target.send(None)

    while data_len > 0:

        data_chunk = data[:data_len]  # slice off the garbage at the end
        data = data[len(data_chunk):]  # slice off what we have read
        data_len -= len(data_chunk)
        target.send(data_chunk)

        if data_len > 0:
            data = yield  # read next report

    target.throw(EOFError())


def encode_wire_v1_message(msg_type, msg_data, target):
    '''Encode a full v1 wire message directly to reports and stream it to target.

Target receives `memoryview`s of HID reports which are valid until the targets
`send()` method returns.
    '''
    report = memoryview(bytearray(_REP_LEN))
    report[0] = REP_MARKER_V1
    serialize_message_header(report, msg_type, len(msg_data))

    source_data = memoryview(msg_data)
    target_data = report[REP_MARKER_V1_LEN + _MSG_HEADER_V1_LEN:]

    while True:
        # move as much as possible from source to target
        n = min(len(target_data), len(source_data))
        target_data[:n] = source_data[:n]
        source_data = source_data[n:]
        target_data = target_data[n:]

        # fill the rest of the report with 0x00
        x = 0
        to_fill = len(target_data)
        while x < to_fill:
            target_data[x] = 0
            x += 1

        target.send(report)

        if not source_data:
            break

        # reset to skip the magic, not the whole header anymore
        target_data = report[REP_MARKER_V1_LEN:]
