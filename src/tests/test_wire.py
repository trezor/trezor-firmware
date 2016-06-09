import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest

from trezor import loop
from trezor import msg
from trezor.wire import read_wire_msg, write_wire_msg
from trezor.utils import chunks


class TestWire(unittest.TestCase):

    def test_read_wire_msg(self):

        # Reading empty message returns correct type and empty bytes

        reader = read_wire_msg()
        reader.send(None)

        empty_message = b'\x3f##\xab\xcd\x00\x00\x00\x00' + b'\x00' * 55
        try:
            reader.send((empty_message,))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, b'')

        # Reading message from one report

        reader = read_wire_msg()
        reader.send(None)

        content = bytes([x for x in range(0, 55)])
        message = b'\x3f##\xab\xcd\x00\x00\x00\x37' + content
        try:
            reader.send((message,))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)

        # Reading message spanning multiple reports

        reader = read_wire_msg()
        reader.send(None)

        content = bytes([x for x in range(0, 256)])
        message = b'##\xab\xcd\x00\x00\x01\00' + content
        reports = [b'\x3f' + ch + '\x00' * (63 - len(ch)) for ch in chunks(message, 63)]
        try:
            for report in reports:
                reader.send((report,))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)

    def test_write_wire_msg(self):

        # Writing message spanning multiple reports calls msg.send() with correct data

        sent_reps = []

        def dummy_send(iface, rep):
            sent_reps.append(bytes(rep))
            return len(rep)

        msg.send = dummy_send

        content = bytes([x for x in range(0, 256)])
        message = b'##\xab\xcd\x00\x00\x01\00' + content
        reports = [b'\x3f' + ch + '\x00' * (63 - len(ch)) for ch in chunks(message, 63)]

        writer = write_wire_msg(int('0xabcd'), content)
        res = 1  # Something not None
        try:
            while True:
                writer.send(None)
        except StopIteration as e:
            res = e.value
        self.assertEqual(res, None)
        self.assertEqual(sent_reps, reports)


if __name__ == '__main__':
    unittest.main()
