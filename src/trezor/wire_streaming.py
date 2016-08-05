import ustruct
import ubinascii

from . import msg
from . import loop
from .crypto import random


MESSAGE_IFACE = const(0)
EMPTY_SESSION = const(0)

sessions = {}


def generate_session_id():
    return random.uniform(0xffffffff) + 1


async def dispatch_reports():
    while True:
        report = await _read_report()
        session_id, report_data = _parse_report(report)
        sessions[session_id].send(report_data)


async def read_session_message(session_id, types):
    future = loop.Future()
    pbuf_decoder = _decode_protobuf_message(types, future)
    wire_decoder = _decode_wire_message(pbuf_decoder)
    assert session_id not in sessions
    sessions[session_id] = wire_decoder
    try:
        result = await future
    finally:
        del sessions[session_id]
    return result


def lookup_protobuf_type(msg_type, pbuf_types):
    for pt in pbuf_types:
        if pt.wire_type == msg_type:
            return pt
    return None


def _decode_protobuf_message(types, future):
    msg_type, _ = yield
    pbuf_type = lookup_protobuf_type(msg_type, types)
    target = build_protobuf_message(pbuf_type, future)
    yield from pbuf_type.load(AsyncBytearrayReader(), target)


class AsyncBytearrayReader:

    def __init__(self, buf=None, n=None):
        self.buf = buf if buf is not None else bytearray()
        self.n = n

    def read(self, n):
        if self.n is not None:
            self.n -= n
            if self.n <= 0:
                raise EOFError()
        buf = self.buf
        while len(buf) < n:
            buf.extend((yield))  # buffer next data chunk
        result, buf[:] = buf[:n], buf[n:]
        return result

    def limit(self, n):
        return AsyncBytearrayReader(self.buf, n)


async def _read_report():
    report, = await loop.Select(MESSAGE_IFACE)
    return memoryview(report)  # make slicing cheap


async def _write_report(report):
    return msg.send(MESSAGE_IFACE, report)


# TREZOR wire protocol v2:
#
# HID report (64B):
# - report magic (1B)
# - session (4B, BE)
# - payload (59B)
#
# message:
# - streamed as payloads of HID reports:
# - message type (4B, BE)
# - data length (4B, BE)
# - data (var-length)
# - data checksum (4B, BE)


REP_HEADER = '>BL'  # marker, session id
MSG_HEADER = '>LL'  # msg type, data length
MSG_FOOTER = '>L'  # data checksum

REP_HEADER_LEN = ustruct.calcsize(REP_HEADER)
MSG_HEADER_LEN = ustruct.calcsize(MSG_HEADER)
MSG_FOOTER_LEN = ustruct.calcsize(MSG_FOOTER)


class MessageChecksumError(Exception):
    pass


def _parse_report(data):
    marker, session_id = ustruct.parse(REP_HEADER, data)
    return session_id, data[REP_HEADER_LEN:]


def _parse_message(data):
    msg_type, data_len = ustruct.parse(MSG_HEADER, data)
    return msg_type, data_len, data[MSG_HEADER_LEN:]


def _parse_footer(data):
    data_checksum, = ustruct.parse(MSG_FOOTER, data)
    return data_checksum,


def _decode_wire_message(target):
    '''Decode a wire message from the report data and stream it to target.

Receives report payloads.
Sends (msg_type, data_len) to target, followed by data chunks.
Throws EOFError after last data chunk, in case of valid checksum.
Throws MessageChecksumError to target if data doesn't match the checksum.
'''
    message = (yield)  # read first report
    msg_type, data_len, data_tail = _parse_message(message)
    target.send((msg_type, data_len))

    checksum = 0  # crc32
    nreports = 1

    while data_len > 0:
        if nreports > 1:
            data_tail = (yield)  # read next report
        nreports += 1

        data_chunk = data_tail[:data_len]  # slice off the garbage at the end
        data_tail = data_tail[len(data_chunk):]  # slice off what we have read
        data_len -= len(data_chunk)
        target.send(data_chunk)

        checksum = ubinascii.crc32(checksum, data_chunk)

    data_footer = data_tail[:MSG_FOOTER_LEN]
    if len(data_footer) < MSG_FOOTER_LEN:
        data_tail = (yield)  # read report with the rest of checksum
        data_footer += data_tail[:MSG_FOOTER_LEN - len(data_footer)]

    data_checksum, = _parse_footer(data_footer)
    if data_checksum != checksum:
        target.throw(MessageChecksumError, 'Message checksum mismatch')
    else:
        target.throw(EOFError)


def _encode_message(target):
    pass
