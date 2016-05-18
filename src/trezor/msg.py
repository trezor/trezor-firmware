import ustruct

from trezor import loop

from TrezorMsg import Msg

_msg = Msg()


def select(timeout_us):
    return _msg.select(timeout_us)


def send(msg):
    return _msg.send(msg)


REPORT_LEN = 64
REPORT_NUM = 63
HEADER_MAGIC = 35  # '#'


def read_report():
    report = yield loop.Select(loop.HID_READ)
    assert report[0] == REPORT_NUM, 'Malformed report number'
    assert len(report) == REPORT_LEN, 'Incorrect report length'
    return memoryview(report)


def parse_header(report):
    assert report[1] == HEADER_MAGIC and report[2] == HEADER_MAGIC, 'Header not found'
    return ustruct.unpack_from('>HL', report, 3)


def read_message():
    report = yield from read_report()
    (msgtype, msglen) = parse_header(report)

    repdata = report[1 + 8:]
    repdata = repdata[:msglen]
    msgbuf = bytearray(repdata)

    remaining = msglen - len(msgbuf)

    while remaining > 0:
        report = yield from read_report()
        repdata = report[1:]
        repdata = repdata[:remaining]
        msgbuf.extend(repdata)
        remaining -= len(repdata)

    return (msgtype, msgbuf)
