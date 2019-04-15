import sys

sys.path.append('../src')

from utest import *
from ubinascii import unhexlify

from trezor import io
from trezor.loop import wait
from trezor.utils import chunks
from trezor.wire import codec_v1


class MockHID:

    def __init__(self, num):
        self.num = num
        self.data = []

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)


def test_reader():
    rep_len = 64
    interface_num = 0xdeadbeef
    message_type = 0x4321
    message_len = 250
    interface = MockHID(interface_num)
    reader = codec_v1.Reader(interface)

    message = bytearray(range(message_len))
    report_header = bytearray(unhexlify('3f23234321000000fa'))

    # open, expected one read
    first_report = report_header + message[:rep_len - len(report_header)]
    assert_async(reader.aopen(), [(None, wait(io.POLL_READ | interface_num)), (first_report, StopIteration()), ])
    assert_eq(reader.type, message_type)
    assert_eq(reader.size, message_len)

    # empty read
    empty_buffer = bytearray()
    assert_async(reader.areadinto(empty_buffer), [(None, StopIteration()), ])
    assert_eq(len(empty_buffer), 0)
    assert_eq(reader.size, message_len)

    # short read, expected no read
    short_buffer = bytearray(32)
    assert_async(reader.areadinto(short_buffer), [(None, StopIteration()), ])
    assert_eq(len(short_buffer), 32)
    assert_eq(short_buffer, message[:len(short_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer))

    # aligned read, expected no read
    aligned_buffer = bytearray(rep_len - len(report_header) - len(short_buffer))
    assert_async(reader.areadinto(aligned_buffer), [(None, StopIteration()), ])
    assert_eq(aligned_buffer, message[len(short_buffer):][:len(aligned_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer) - len(aligned_buffer))

    # one byte read, expected one read
    next_report_header = bytearray(unhexlify('3f'))
    next_report = next_report_header + message[rep_len - len(report_header):][:rep_len - len(next_report_header)]
    onebyte_buffer = bytearray(1)
    assert_async(reader.areadinto(onebyte_buffer), [(None, wait(io.POLL_READ | interface_num)), (next_report, StopIteration()), ])
    assert_eq(onebyte_buffer, message[len(short_buffer):][len(aligned_buffer):][:len(onebyte_buffer)])
    assert_eq(reader.size, message_len - len(short_buffer) - len(aligned_buffer) - len(onebyte_buffer))

    # too long read, raises eof
    assert_async(reader.areadinto(bytearray(reader.size + 1)), [(None, EOFError()), ])

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
        expected_syscalls.append((prev_report, wait(io.POLL_READ | interface_num)))
    expected_syscalls.append((next_reports[-1], StopIteration()))
    assert_async(reader.areadinto(long_buffer), expected_syscalls)
    assert_eq(long_buffer, message[-start_size:])
    assert_eq(reader.size, 0)

    # one byte read, raises eof
    assert_async(reader.areadinto(onebyte_buffer), [(None, EOFError()), ])


def test_writer():
    rep_len = 64
    interface_num = 0xdeadbeef
    message_type = 0x87654321
    message_len = 1024
    interface = MockHID(interface_num)
    writer = codec_v1.Writer(interface)
    writer.setheader(message_type, message_len)

    # init header corresponding to the data above
    report_header = bytearray(unhexlify('3f2323432100000400'))

    assert_eq(writer.data, report_header + bytearray(rep_len - len(report_header)))

    # empty write
    start_size = writer.size
    assert_async(writer.awrite(bytearray()), [(None, StopIteration()), ])
    assert_eq(writer.data, report_header + bytearray(rep_len - len(report_header)))
    assert_eq(writer.size, start_size)

    # short write, expected no report
    start_size = writer.size
    short_payload = bytearray(range(4))
    assert_async(writer.awrite(short_payload), [(None, StopIteration()), ])
    assert_eq(writer.size, start_size - len(short_payload))
    assert_eq(writer.data,
              report_header +
              short_payload +
              bytearray(rep_len - len(report_header) - len(short_payload)))

    # aligned write, expected one report
    start_size = writer.size
    aligned_payload = bytearray(range(rep_len - len(report_header) - len(short_payload)))
    assert_async(writer.awrite(aligned_payload), [(None, wait(io.POLL_WRITE | interface_num)), (None, StopIteration()), ])
    assert_eq(interface.data, [report_header +
                               short_payload +
                               aligned_payload +
                               bytearray(rep_len - len(report_header) - len(short_payload) - len(aligned_payload)), ])
    assert_eq(writer.size, start_size - len(aligned_payload))
    interface.data.clear()

    # short write, expected no report, but data starts with correct seq and cont marker
    report_header = bytearray(unhexlify('3f'))
    start_size = writer.size
    assert_async(writer.awrite(short_payload), [(None, StopIteration()), ])
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
    assert_async(writer.awrite(long_payload), len(expected_write_reports) * [(None, wait(io.POLL_WRITE | interface_num))] + [(None, StopIteration())])
    assert_eq(interface.data, expected_write_reports)
    assert_eq(writer.size, start_size - len(long_payload))
    interface.data.clear()
    # test write raises eof
    assert_async(writer.awrite(bytearray(1)), [(None, EOFError())])
    assert_eq(interface.data, [])
    # test close
    expected_close_reports = expected_reports[-1:]
    assert_async(writer.aclose(), len(expected_close_reports) * [(None, wait(io.POLL_WRITE | interface_num))] + [(None, StopIteration())])
    assert_eq(interface.data, expected_close_reports)
    assert_eq(writer.size, 0)


if __name__ == '__main__':
    run_tests()
