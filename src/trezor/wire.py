import ustruct
from . import msg
from . import loop

IFACE = const(0)

REPORT_LEN = const(64)
REPORT_NUM = const(63)
HEADER_MAGIC = const(35)  #


def read_report():
    rep, = yield loop.Select(IFACE)
    assert rep[0] == REPORT_NUM, 'Report number malformed'
    return rep


def write_report(rep):
    size = msg.send(IFACE, rep)
    assert size == REPORT_LEN, 'HID write failed'


def read_wire_msg():
    rep = yield from read_report()
    assert rep[1] == HEADER_MAGIC
    assert rep[2] == HEADER_MAGIC
    (mtype, mlen) = ustruct.unpack_from('>HL', rep, 3)

    # TODO: validate mlen for sane values

    rep = memoryview(rep)
    data = rep[9:]
    data = data[:mlen]

    mbuf = bytearray(data)  # TODO: allocate mlen bytes
    remaining = mlen - len(mbuf)

    while remaining > 0:
        rep = yield from read_report()
        rep = memoryview(rep)
        data = rep[1:]
        data = data[:remaining]
        mbuf.extend(data)
        remaining -= len(data)

    return (mtype, mbuf)


def write_wire_msg(mtype, mbuf):
    rep = bytearray(REPORT_LEN)
    rep[0] = REPORT_NUM
    rep[1] = HEADER_MAGIC
    rep[2] = HEADER_MAGIC
    ustruct.pack_into('>HL', rep, 3, mtype, len(mbuf))

    rep = memoryview(rep)
    mbuf = memoryview(mbuf)
    data = rep[9:]

    while mbuf:
        n = min(len(data), len(mbuf))
        data[:n] = mbuf[:n]
        i = n
        while i < len(data):
            data[i] = 0
            i += 1
        write_report(rep)
        mbuf = mbuf[n:]
        data = rep[1:]


def read(*types):
    mtype, mbuf = yield from read_wire_msg()
    for t in types:
        if t.wire_type == mtype:
            return t.loads(mbuf)
    else:
        raise Exception('Unexpected message')


def write(m):
    mbuf = m.dumps()
    mtype = m.message_type.wire_type
    write_wire_msg(mtype, mbuf)


def call(req, *types):
    write(req)
    res = yield from read(*types)
    return res
