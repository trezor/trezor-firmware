from common import *
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


class TestWireCodecV1(unittest.TestCase):

    def test_reader(self):
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
        self.assertAsync(reader.aopen(), [(None, wait(io.POLL_READ | interface_num)), (first_report, StopIteration()), ])
        self.assertEqual(reader.type, message_type)
        self.assertEqual(reader.size, message_len)

        # empty read
        empty_buffer = bytearray()
        self.assertAsync(reader.areadinto(empty_buffer), [(None, StopIteration()), ])
        self.assertEqual(len(empty_buffer), 0)
        self.assertEqual(reader.size, message_len)

        # short read, expected no read
        short_buffer = bytearray(32)
        self.assertAsync(reader.areadinto(short_buffer), [(None, StopIteration()), ])
        self.assertEqual(len(short_buffer), 32)
        self.assertEqual(short_buffer, message[:len(short_buffer)])
        self.assertEqual(reader.size, message_len - len(short_buffer))

        # aligned read, expected no read
        aligned_buffer = bytearray(rep_len - len(report_header) - len(short_buffer))
        self.assertAsync(reader.areadinto(aligned_buffer), [(None, StopIteration()), ])
        self.assertEqual(aligned_buffer, message[len(short_buffer):][:len(aligned_buffer)])
        self.assertEqual(reader.size, message_len - len(short_buffer) - len(aligned_buffer))

        # one byte read, expected one read
        next_report_header = bytearray(unhexlify('3f'))
        next_report = next_report_header + message[rep_len - len(report_header):][:rep_len - len(next_report_header)]
        onebyte_buffer = bytearray(1)
        self.assertAsync(reader.areadinto(onebyte_buffer), [(None, wait(io.POLL_READ | interface_num)), (next_report, StopIteration()), ])
        self.assertEqual(onebyte_buffer, message[len(short_buffer):][len(aligned_buffer):][:len(onebyte_buffer)])
        self.assertEqual(reader.size, message_len - len(short_buffer) - len(aligned_buffer) - len(onebyte_buffer))

        # too long read, raises eof
        self.assertAsync(reader.areadinto(bytearray(reader.size + 1)), [(None, EOFError()), ])

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
        self.assertAsync(reader.areadinto(long_buffer), expected_syscalls)
        self.assertEqual(long_buffer, message[-start_size:])
        self.assertEqual(reader.size, 0)

        # one byte read, raises eof
        self.assertAsync(reader.areadinto(onebyte_buffer), [(None, EOFError()), ])


    def test_writer(self):
        rep_len = 64
        interface_num = 0xdeadbeef
        message_type = 0x87654321
        message_len = 1024
        interface = MockHID(interface_num)
        writer = codec_v1.Writer(interface)
        writer.setheader(message_type, message_len)

        # init header corresponding to the data above
        report_header = bytearray(unhexlify('3f2323432100000400'))

        self.assertEqual(writer.data, report_header + bytearray(rep_len - len(report_header)))

        # empty write
        start_size = writer.size
        self.assertAsync(writer.awrite(bytearray()), [(None, StopIteration()), ])
        self.assertEqual(writer.data, report_header + bytearray(rep_len - len(report_header)))
        self.assertEqual(writer.size, start_size)

        # short write, expected no report
        start_size = writer.size
        short_payload = bytearray(range(4))
        self.assertAsync(writer.awrite(short_payload), [(None, StopIteration()), ])
        self.assertEqual(writer.size, start_size - len(short_payload))
        self.assertEqual(writer.data,
                  report_header +
                  short_payload +
                  bytearray(rep_len - len(report_header) - len(short_payload)))

        # aligned write, expected one report
        start_size = writer.size
        aligned_payload = bytearray(range(rep_len - len(report_header) - len(short_payload)))
        self.assertAsync(writer.awrite(aligned_payload), [(None, wait(io.POLL_WRITE | interface_num)), (None, StopIteration()), ])
        self.assertEqual(interface.data, [report_header +
                                   short_payload +
                                   aligned_payload +
                                   bytearray(rep_len - len(report_header) - len(short_payload) - len(aligned_payload)), ])
        self.assertEqual(writer.size, start_size - len(aligned_payload))
        interface.data.clear()

        # short write, expected no report, but data starts with correct seq and cont marker
        report_header = bytearray(unhexlify('3f'))
        start_size = writer.size
        self.assertAsync(writer.awrite(short_payload), [(None, StopIteration()), ])
        self.assertEqual(writer.size, start_size - len(short_payload))
        self.assertEqual(writer.data[:len(report_header) + len(short_payload)],
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
        self.assertAsync(writer.awrite(long_payload), len(expected_write_reports) * [(None, wait(io.POLL_WRITE | interface_num))] + [(None, StopIteration())])
        self.assertEqual(interface.data, expected_write_reports)
        self.assertEqual(writer.size, start_size - len(long_payload))
        interface.data.clear()
        # test write raises eof
        self.assertAsync(writer.awrite(bytearray(1)), [(None, EOFError())])
        self.assertEqual(interface.data, [])
        # test close
        expected_close_reports = expected_reports[-1:]
        self.assertAsync(writer.aclose(), len(expected_close_reports) * [(None, wait(io.POLL_WRITE | interface_num))] + [(None, StopIteration())])
        self.assertEqual(interface.data, expected_close_reports)
        self.assertEqual(writer.size, 0)


if __name__ == '__main__':
    unittest.main()
