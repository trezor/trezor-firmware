import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest

from trezor import loop
from trezor import msg
from trezor.msg import read_wire_msg, write_wire_msg


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


class TestMsg(unittest.TestCase):

    def test_read_wire_msg(self):

        reader = read_wire_msg()
        reader.send(None)

        empty_message = b'\x3f##\xab\xcd\x00\x00\x00\x00' + b'\x00' * 55
        try:
            reader.send((loop.HID_READ, empty_message))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, b'')

        reader = read_wire_msg()
        reader.send(None)

        content = bytes([x for x in range(0, 55)])
        message = b'\x3f##\xab\xcd\x00\x00\x00\x37' + content
        try:
            reader.send((loop.HID_READ, message))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)

        reader = read_wire_msg()
        reader.send(None)

        content = bytes([x for x in range(0, 256)])
        message = b'##\xab\xcd\x00\x00\x01\00' + content
        reports = [b'\x3f' + ch + '\x00' * (63 - len(ch)) for ch in chunks(message, 63)]
        try:
            for report in reports:
                reader.send((loop.HID_READ, report))
        except StopIteration as e:
            restype, resmsg = e.value
        self.assertEqual(restype, int('0xabcd', 16))
        self.assertEqual(resmsg, content)

    def test_write_wire_msg(self):

        sent_reps = []
        msg.send = lambda rep: sent_reps.append(bytes(rep))

        content = bytes([x for x in range(0, 256)])
        message = b'##\xab\xcd\x00\x00\x01\00' + content
        reports = [b'\x3f' + ch + '\x00' * (63 - len(ch)) for ch in chunks(message, 63)]
        write_wire_msg(int('0xabcd'), content)
        self.assertEqual(sent_reps, reports)


if __name__ == '__main__':
    unittest.main()
