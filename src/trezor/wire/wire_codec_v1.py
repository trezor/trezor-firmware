from micropython import const
import ustruct

SESSION_V1 = const(0)
REP_MARKER_V1 = const(63)  # ord('?)
REP_MARKER_V1_LEN = const(1)  # len('?')

_REP_LEN = const(64)
_MSG_HEADER_MAGIC = const(35)  # org('#')
_MSG_HEADER_V1 = '>BBHL'  # magic, magic, wire type, data length
_MSG_HEADER_V1_LEN = ustruct.calcsize(_MSG_HEADER_V1)


def detect_v1(data):
    return (data[0] == REP_MARKER_V1)


def parse_report_v1(data):
    return None, SESSION_V1, data[1:]


def parse_message(data):
    magic1, magic2, msg_type, data_len = ustruct.unpack(_MSG_HEADER_V1, data)
    if magic1 != _MSG_HEADER_MAGIC or magic2 != _MSG_HEADER_MAGIC:
        raise Exception('Corrupted magic bytes')

    return msg_type, data_len, data[_MSG_HEADER_V1_LEN:]


def serialize_message_header(data, msg_type, msg_len):
    ustruct.pack_into(
        _MSG_HEADER_V1, data, REP_MARKER_V1_LEN,
        _MSG_HEADER_MAGIC, _MSG_HEADER_MAGIC, msg_type, msg_len)


def decode_wire_v1_stream(genfunc, session_id, *args):
    '''Decode a v1 wire message from the report data and stream it to target.

Receives report payloads.
Sends (msg_type, data_len) to target, followed by data chunks.
Throws EOFError after last data chunk, in case of valid checksum.
Throws MessageChecksumError to target if data doesn't match the checksum.
'''

    message = yield  # read first report
    msg_type, data_len, data = parse_message(message)

    print(msg_type, data_len, bytes(data))
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

        # FIXME: optimize speed
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
