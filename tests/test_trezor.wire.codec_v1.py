import sys

sys.path.append('../src')
sys.path.append('../src/lib')

from utest import *
from ustruct import pack, unpack
from ubinascii import hexlify, unhexlify

from trezor import msg
from trezor.loop import Select, Syscall, READ, WRITE
from trezor.crypto import random
from trezor.utils import chunks
from trezor.wire import codec_v1


def test_reader():
    rep_len = 64
    interface = 0xdeadbeef
    message_type = 0x4321
    message_len = 250
    reader = codec_v1.Reader(interface, codec_v1.SESSION_ID)

    message = bytearray(range(message_len))
    report_header = bytearray(unhexlify('3f23234321000000fa'))

    # open, expected one read
    first_report = report_header + message[:rep_len - len(report_header)]
    assert_async(reader.open(), [(None, Select(READ | interface)), (first_report, StopIteration()),])
    assert_eq(reader.type, message_type)
    assert_eq(reader.size, message_len)

    # empty read
    empty_buffer = bytearray()
    assert_async(reader.readinto(empty_buffer), [(None, StopIteration()),])
    assert_eq(len(empty_buffer), 0)
    assert_eq(reader.size, message_len)

    # short read, expected no read
    short_buffer = bytearray(32)
    assert_async(reader.readinto(short_buffer), [(None, StopIteration()),])
    assert_eq(len(short_buffer), 32)
    assert_eq(short_buffer, message[:len(short_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer))

    # aligned read, expected no read
    aligned_buffer = bytearray(rep_len - len(report_header) - len(short_buffer))
    assert_async(reader.readinto(aligned_buffer), [(None, StopIteration()),])
    assert_eq(aligned_buffer, message[len(short_buffer):][:len(aligned_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer) - len(aligned_buffer))

    # one byte read, expected one read
    next_report_header = bytearray(unhexlify('3f'))
    next_report = next_report_header + message[rep_len - len(report_header):][:rep_len - len(next_report_header)]
    onebyte_buffer = bytearray(1)
    assert_async(reader.readinto(onebyte_buffer), [(None, Select(READ | interface)), (next_report, StopIteration()),])
    assert_eq(onebyte_buffer, message[len(short_buffer):][len(aligned_buffer):][:len(onebyte_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer) - len(aligned_buffer) - len(onebyte_buffer))

    # too long read, raises eof
    assert_async(reader.readinto(bytearray(reader.size + 1)), [(None, EOFError()),])

    # long read, expect multiple reads
    start_size = reader.size
    long_buffer = bytearray(start_size)
    report_payload = message[rep_len - len(report_header) + rep_len - len(next_report_header):]
    report_payload_head = report_payload[:rep_len - len(next_report_header) - len(onebyte_buffer)]
    report_payload_rest = report_payload[len(report_payload_head):]
    report_payload_rest = list(chunks(report_payload_rest, rep_len - len(next_report_header)))
    report_payloads = [report_payload_head] + report_payload_rest
    next_reports = [next_report_header + r for r in report_payloads]
    expected_syscalls = []
    for i, _ in enumerate(next_reports):
        prev_report = next_reports[i - 1] if i > 0 else None
        expected_syscalls.append((prev_report, Select(READ | interface)))
    expected_syscalls.append((next_reports[-1], StopIteration()))
    assert_async(reader.readinto(long_buffer), expected_syscalls)
    assert_eq(long_buffer, message[-start_size:])
    assert_eq(reader.size, 0)

    # one byte read, raises eof
    assert_async(reader.readinto(onebyte_buffer), [(None, EOFError()),])


def test_writer():
    rep_len = 64
    interface = 0xdeadbeef
    message_type = 0x87654321
    message_len = 1024
    writer = codec_v1.Writer(interface, codec_v1.SESSION_ID, message_type, message_len)

    # init header corresponding to the data above
    report_header = bytearray(unhexlify('3f2323432100000400'))

    assert_eq(writer.data, report_header + bytearray(rep_len - len(report_header)))

    # empty write
    start_size = writer.size
    assert_async(writer.write(bytearray()), [(None, StopIteration()),])
    assert_eq(writer.data, report_header + bytearray(rep_len - len(report_header)))
    assert_eq(writer.size, start_size)

    # short write, expected no report
    start_size = writer.size
    short_payload = bytearray(range(4))
    assert_async(writer.write(short_payload), [(None, StopIteration()),])
    assert_eq(writer.size, start_size - len(short_payload))
    assert_eq(writer.data,
              report_header
              + short_payload
              + bytearray(rep_len - len(report_header) - len(short_payload)))

    # aligned write, expected one report
    start_size = writer.size
    aligned_payload = bytearray(range(rep_len - len(report_header) - len(short_payload)))
    msg.send = mock_call(msg.send, [
        (interface, report_header
         + short_payload
         + aligned_payload
         + bytearray(rep_len - len(report_header) - len(short_payload) - len(aligned_payload))), ])
    assert_async(writer.write(aligned_payload), [(None, Select(WRITE | interface)), (None, StopIteration()),])
    assert_eq(writer.size, start_size - len(aligned_payload))
    msg.send.assert_called_n_times(1)
    msg.send = msg.send.original

    # short write, expected no report, but data starts with correct seq and cont marker
    report_header = bytearray(unhexlify('3f'))
    start_size = writer.size
    assert_async(writer.write(short_payload), [(None, StopIteration()),])
    assert_eq(writer.size, start_size - len(short_payload))
    assert_eq(writer.data[:len(report_header) + len(short_payload)],
              report_header + short_payload)

    # long write, expected multiple reports
    start_size = writer.size
    long_payload_head = bytearray(range(rep_len - len(report_header) - len(short_payload)))
    long_payload_rest = bytearray(range(start_size - len(long_payload_head)))
    long_payload = long_payload_head + long_payload_rest
    expected_payloads = [short_payload + long_payload_head] + list(chunks(long_payload_rest, rep_len - len(report_header)))
    expected_reports = [report_header + r for r in expected_payloads]
    expected_reports[-1] += bytearray(bytes(1) * (rep_len - len(expected_reports[-1])))
    # test write
    expected_write_reports = expected_reports[:-1]
    msg.send = mock_call(msg.send, [(interface, rep) for rep in expected_write_reports])
    assert_async(writer.write(long_payload), len(expected_write_reports) * [(None, Select(WRITE | interface))] + [(None, StopIteration())])
    assert_eq(writer.size, start_size - len(long_payload))
    msg.send.assert_called_n_times(len(expected_write_reports))
    msg.send = msg.send.original
    # test write raises eof
    msg.send = mock_call(msg.send, [])
    assert_async(writer.write(bytearray(1)), [(None, EOFError())])
    msg.send.assert_called_n_times(0)
    msg.send = msg.send.original
    # test close
    expected_close_reports = expected_reports[-1:]
    msg.send = mock_call(msg.send, [(interface, rep) for rep in expected_close_reports])
    assert_async(writer.close(), len(expected_close_reports) * [(None, Select(WRITE | interface))] + [(None, StopIteration())])
    assert_eq(writer.size, 0)
    msg.send.assert_called_n_times(len(expected_close_reports))
    msg.send = msg.send.original


if __name__ == '__main__':
    run_tests()
