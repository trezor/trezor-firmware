from common import *

import ustruct
import ubinascii

from trezor.crypto import random
from trezor.utils import chunks

from trezor.wire import codec

class TestWireCodec(unittest.TestCase):
    # pylint: disable=C0301

    def test_parse(self):
        d = b'O' + b'\x01\x23\x45\x67' + bytes(range(0, 59))

        m, s, d = codec.parse_report(d)
        self.assertEqual(m, b'O'[0])
        self.assertEqual(s, 0x01234567)
        self.assertEqual(d, bytes(range(0, 59)))

        t, l, d = codec.parse_message(d)
        self.assertEqual(t, 0x00010203)
        self.assertEqual(l, 0x04050607)
        self.assertEqual(d, bytes(range(8, 59)))

        f, = codec.parse_message_footer(d[0:4])
        self.assertEqual(f, 0x08090a0b)

        for i in range(0, 1024):
            if i != 64:
                with self.assertRaises(ValueError):
                    codec.parse_report(bytes(range(0, i)))
            if i != 59:
                with self.assertRaises(ValueError):
                    codec.parse_message(bytes(range(0, i)))
            if i != 4:
                with self.assertRaises(ValueError):
                    codec.parse_message_footer(bytes(range(0, i)))

    def test_serialize(self):
        data = bytearray(range(0, 6))
        codec.serialize_report_header(data, 0x12, 0x3456789a)
        self.assertEqual(data, b'\x12\x34\x56\x78\x9a\x05')

        data = bytearray(range(0, 6))
        codec.serialize_opened_session(data, 0x3456789a)
        self.assertEqual(data, bytes([codec.REP_MARKER_OPEN]) + b'\x34\x56\x78\x9a\x05')

        data = bytearray(range(0, 14))
        codec.serialize_message_header(data, 0x01234567, 0x89abcdef)
        self.assertEqual(data, b'\x00\x01\x02\x03\x04\x01\x23\x45\x67\x89\xab\xcd\xef\x0d')

        data = bytearray(range(0, 5))
        codec.serialize_message_footer(data, 0x89abcdef)
        self.assertEqual(data, b'\x89\xab\xcd\xef\x04')

        for i in range(0, 13):
            data = bytearray(i)
            if i < 4:
                with self.assertRaises(ValueError):
                    codec.serialize_message_footer(data, 0x00)
            if i < 5:
                with self.assertRaises(ValueError):
                    codec.serialize_report_header(data, 0x00, 0x00)
                with self.assertRaises(ValueError):
                    codec.serialize_opened_session(data, 0x00)
            with self.assertRaises(ValueError):
                codec.serialize_message_header(data, 0x00, 0x00)

    def test_decode_empty(self):
        message = b'\xab\xcd\xef\x12' + b'\x00\x00\x00\x00' + b'\x00' * 51

        record = []
        genfunc = self._record(record, 0xabcdef12, 0, 0xdeadbeef, 'dummy')
        decoder = codec.decode_wire_stream(genfunc, 0xdeadbeef, 'dummy')
        decoder.send(None)

        try:
            decoder.send(message)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(len(record), 1)
        self.assertIsInstance(record[0], EOFError)

    def test_decode_one_report_aligned_correct(self):
        data = bytes(range(0, 47))
        footer = b'\x2f\x1c\x12\xce'
        message = b'\xab\xcd\xef\x12' + b'\x00\x00\x00\x2f' + data + footer

        record = []
        genfunc = self._record(record, 0xabcdef12, 47, 0xdeadbeef, 'dummy')
        decoder = codec.decode_wire_stream(genfunc, 0xdeadbeef, 'dummy')
        decoder.send(None)

        try:
            decoder.send(message)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(len(record), 2)
        self.assertEqual(record[0], data)
        self.assertIsInstance(record[1], EOFError)

    def test_decode_one_report_aligned_incorrect(self):
        data = bytes(range(0, 47))
        footer = bytes(4)  # wrong checksum
        message = b'\xab\xcd\xef\x12' + b'\x00\x00\x00\x2f' + data + footer

        record = []
        genfunc = self._record(record, 0xabcdef12, 47, 0xdeadbeef, 'dummy')
        decoder = codec.decode_wire_stream(genfunc, 0xdeadbeef, 'dummy')
        decoder.send(None)

        try:
            decoder.send(message)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(len(record), 2)
        self.assertEqual(record[0], data)
        self.assertIsInstance(record[1], codec.MessageChecksumError)

    def test_decode_generated_range(self):
        for data_len in range(1, 512):
            data = random.bytes(data_len)
            data_chunks = [data[:51]] + list(chunks(data[51:], 59))

            msg_type = 0xabcdef12
            data_csum = ubinascii.crc32(data)
            header = ustruct.pack('>L', msg_type) + ustruct.pack('>L', data_len)
            footer = ustruct.pack('>L', data_csum)

            message = header + data + footer
            message_chunks = [c + '\x00' * (59 - len(c)) for c in list(chunks(message, 59))]

            record = []
            genfunc = self._record(record, msg_type, data_len, 0xdeadbeef, 'dummy')
            decoder = codec.decode_wire_stream(genfunc, 0xdeadbeef, 'dummy')
            decoder.send(None)

            res = 1
            try:
                for c in message_chunks:
                    decoder.send(c)
            except StopIteration as e:
                res = e.value
            self.assertEqual(res, None)
            self.assertEqual(len(record), len(data_chunks) + 1)
            for i in range(0, len(data_chunks)):
                self.assertEqual(record[i], data_chunks[i])
            self.assertIsInstance(record[-1], EOFError)

    def test_encode_empty(self):
        record = []
        target = self._record(record)()
        target.send(None)

        codec.encode_wire_message(0xabcdef12, b'', 0xdeadbeef, target)
        self.assertEqual(len(record), 1)
        self.assertEqual(record[0], b'H\xde\xad\xbe\xef\xab\xcd\xef\x12\x00\x00\x00\x00' + '\0' * 51)

    def test_encode_one_report_aligned(self):
        data = bytes(range(0, 47))
        footer = b'\x2f\x1c\x12\xce'

        record = []
        target = self._record(record)()
        target.send(None)

        codec.encode_wire_message(0xabcdef12, data, 0xdeadbeef, target)
        self.assertEqual(record, [b'H\xde\xad\xbe\xef\xab\xcd\xef\x12\x00\x00\x00\x2f' + data + footer])

    def test_encode_generated_range(self):
        for data_len in range(1, 1024):
            data = random.bytes(data_len)

            msg_type = 0xabcdef12
            session_id = 0xdeadbeef

            data_csum = ubinascii.crc32(data)
            header = ustruct.pack('>L', msg_type) + ustruct.pack('>L', data_len)
            footer = ustruct.pack('>L', data_csum)
            session_header = ustruct.pack('>L', session_id)

            message = header + data + footer
            report0 = b'H' + session_header + message[:59]
            reports = [b'D' + session_header + c for c in chunks(message[59:], 59)]
            reports.insert(0, report0)
            reports[-1] = reports[-1] + b'\x00' * (64 - len(reports[-1]))

            received = 0
            def genfunc():
                nonlocal received
                while True:
                    self.assertEqual((yield), reports[received])
                    received += 1
            target = genfunc()
            target.send(None)

            codec.encode_wire_message(msg_type, data, session_id, target)
            self.assertEqual(received, len(reports))

    def _record(self, record, *_args):
        def genfunc(*args):
            self.assertEqual(args, _args)
            while True:
                try:
                    v = yield
                except Exception as e:
                    record.append(e)
                else:
                    record.append(v)
        return genfunc


if __name__ == '__main__':
    unittest.main()
