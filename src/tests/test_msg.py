import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest

from trezor import loop
from trezor.msg import read_report, parse_header, read_message


class TestMsg(unittest.TestCase):

    def test_read_report(self):

        reader = read_report()
        syscall = reader.send(None)

        self.assertIsInstance(syscall, loop.Select)
        self.assertEqual(syscall.events, (loop.HID_READ,))

        empty_report = b'\x3f' + b'\x00' * 63
        try:
            reader.send(empty_report)
        except StopIteration as e:
            result = e.value
        self.assertEqual(result, empty_report)

    def test_parse_header(self):

        report = b'\x3f##\xab\xcd\x12\x34\x56\x78'
        msgtype, msglen = parse_header(report)
        self.assertEqual(msgtype, int('0xabcd', 16))
        self.assertEqual(msglen, int('0x12345678', 16))

    def test_read_message(self):

        reader = read_message()
        reader.send(None)

        empty_message = b'\x3f##\xab\xcd\x00\x00\x00\x00' + b'\x00' * 55
        try:
            reader.send(empty_message)
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, b'')

        reader = read_message()
        reader.send(None)

        content = bytes([x for x in range(0, 55)])
        message = b'\x3f##\xab\xcd\x00\x00\x00\x37' + content
        try:
            reader.send(message)
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)

        def chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i + n]

        reader = read_message()
        reader.send(None)

        content = bytes([x for x in range(0, 256)])
        message = b'##\xab\xcd\x00\x00\x01\00' + content
        reports = [b'\x3f' + ch + '\x00' * (63 - len(ch)) for ch in chunks(message, 63)]
        try:
            for report in reports:
                reader.send(report)
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)


if __name__ == '__main__':
    unittest.main()
