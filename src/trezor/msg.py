import ustruct

from trezor import loop

from TrezorMsg import Msg

_msg = Msg()


def select(timeout_us):
    return _msg.select(timeout_us)


def send(msg):
    return _msg.send(msg)


REPORT_LEN = const(64)
REPORT_NUM = const(63)
HEADER_MAGIC = const(35)  # '#'


def read_report():
    report = yield loop.Select(loop.HID_READ)
    assert report[0] == REPORT_NUM
    return report


def write_report(report):
    return send(report)  # FIXME


def read_message():
    report = yield from read_report()
    assert report[1] == HEADER_MAGIC
    assert report[2] == HEADER_MAGIC
    (msgtype, msglen) = ustruct.unpack_from('>HL', report, 3)

    # TODO: validate msglen for sane values

    report = memoryview(report)
    data = report[9:]
    data = data[:msglen]

    msgdata = bytearray(data)  # TODO: allocate msglen bytes
    remaining = msglen - len(msgdata)

    while remaining > 0:
        report = yield from read_report()
        report = memoryview(report)
        data = report[1:]
        data = data[:remaining]
        msgdata.extend(data)
        remaining -= len(data)

    return (msgtype, msgdata)


def write_message(msgtype, msgdata):
    report = bytearray(REPORT_LEN)
    report[0] = REPORT_NUM
    report[1] = HEADER_MAGIC
    report[2] = HEADER_MAGIC
    ustruct.pack_into('>HL', report, 3, msgtype, len(msgdata))

    msgdata = memoryview(msgdata)
    report = memoryview(report)
    data = report[9:]

    while msgdata:
        n = min(len(data), len(msgdata))
        data[:n] = msgdata[:n]
        i = n
        while i < len(data):
            data[i] = 0
            i += 1
        write_report(report)
        msgdata = msgdata[n:]
        data = report[1:]
