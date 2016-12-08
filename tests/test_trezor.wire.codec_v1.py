from common import *

import ustruct

from trezor.crypto import random
from trezor.utils import chunks

from trezor.wire import codec_v1

class TestWireCodecV1(unittest.TestCase):
    # pylint: disable=C0301

    def test_detect(self):
        for i in range(0, 256):
            if i == ord(b'?'):
                self.assertTrue(codec_v1.detect(bytes([i]) + b'\x00' * 63))
            else:
                self.assertFalse(codec_v1.detect(bytes([i]) + b'\x00' * 63))

    def test_parse(self):
        d = bytes(range(0, 55))
        m = b'##\x00\x00\x00\x00\x00\x37' + d
        r = b'?' + m

        rm, rs, rd = codec_v1.parse_report(r)
        self.assertEqual(rm, None)
        self.assertEqual(rs, 0)
        self.assertEqual(rd, m)

        mt, ml, md = codec_v1.parse_message(m)
        self.assertEqual(mt, 0)
        self.assertEqual(ml, len(d))
        self.assertEqual(md, d)

        for i in range(0, 1024):
            if i != 64:
                with self.assertRaises(ValueError):
                    codec_v1.parse_report(bytes(range(0, i)))

        for hx in range(0, 256):
            for hy in range(0, 256):
                if hx != ord(b'#') and hy != ord(b'#'):
                    with self.assertRaises(ValueError):
                        codec_v1.parse_message(bytes([hx, hy]) + m[2:])

    def test_serialize(self):
        data = bytearray(range(0, 10))
        codec_v1.serialize_message_header(data, 0x1234, 0x56789abc)
        self.assertEqual(data, b'\x00##\x12\x34\x56\x78\x9a\xbc\x09')

        data = bytearray(9)
        with self.assertRaises(ValueError):
            codec_v1.serialize_message_header(data, 65536, 0)

        for i in range(0, 8):
            data = bytearray(i)
            with self.assertRaises(ValueError):
                codec_v1.serialize_message_header(data, 0x1234, 0x56789abc)

    def test_decode_empty(self):
        message = b'##' + b'\xab\xcd' + b'\x00\x00\x00\x00' + b'\x00' * 55

        record = []
        genfunc = self._record(record, 0xdeadbeef, 0xabcd, 0, 'dummy')
        decoder = codec_v1.decode_stream(0xdeadbeef, genfunc, 'dummy')
        decoder.send(None)

        try:
            decoder.send(message)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(len(record), 1)
        self.assertIsInstance(record[0], EOFError)

    def test_decode_one_report_aligned(self):
        data = bytes(range(0, 55))
        message = b'##' + b'\xab\xcd' + b'\x00\x00\x00\x37' + data

        record = []
        genfunc = self._record(record, 0xdeadbeef, 0xabcd, 55, 'dummy')
        decoder = codec_v1.decode_stream(0xdeadbeef, genfunc, 'dummy')
        decoder.send(None)

        try:
            decoder.send(message)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(len(record), 2)
        self.assertEqual(record[0], data)
        self.assertIsInstance(record[1], EOFError)

    def test_decode_generated_range(self):
        for data_len in range(1, 512):
            data = random.bytes(data_len)
            data_chunks = [data[:55]] + list(chunks(data[55:], 63))

            msg_type = 0xabcd
            header = b'##' + ustruct.pack('>H', msg_type) + ustruct.pack('>L', data_len)

            message = header + data
            message_chunks = [c + '\x00' * (63 - len(c)) for c in list(chunks(message, 63))]

            record = []
            genfunc = self._record(record, 0xdeadbeef, msg_type, data_len, 'dummy')
            decoder = codec_v1.decode_stream(0xdeadbeef, genfunc, 'dummy')
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

        codec_v1.encode(codec_v1.SESSION, 0xabcd, b'', target.send)
        self.assertEqual(len(record), 1)
        self.assertEqual(record[0], b'?##\xab\xcd\x00\x00\x00\x00' + '\0' * 55)

    def test_encode_one_report_aligned(self):
        data = bytes(range(0, 55))

        record = []
        target = self._record(record)()
        target.send(None)

        codec_v1.encode(codec_v1.SESSION, 0xabcd, data, target.send)
        self.assertEqual(record, [b'?##\xab\xcd\x00\x00\x00\x37' + data])

    def test_encode_generated_range(self):
        for data_len in range(1, 1024):
            data = random.bytes(data_len)

            msg_type = 0xabcd
            header = b'##' + ustruct.pack('>H', msg_type) + ustruct.pack('>L', data_len)

            message = header + data
            reports = [b'?' + c for c in chunks(message, 63)]
            reports[-1] = reports[-1] + b'\x00' * (64 - len(reports[-1]))

            received = 0
            def genfunc():
                nonlocal received
                while True:
                    self.assertEqual((yield), reports[received])
                    received += 1
            target = genfunc()
            target.send(None)

            codec_v1.encode(codec_v1.SESSION, msg_type, data, target.send)
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
