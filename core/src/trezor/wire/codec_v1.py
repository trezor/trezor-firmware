import ustruct
from micropython import const

from trezor import io, loop, utils

_REP_LEN = const(64)

_REP_MARKER = const(63)  # ord('?')
_REP_MAGIC = const(35)  # org('#')
_REP_INIT = ">BBBHL"  # marker, magic, magic, wire type, data length
_REP_INIT_DATA = const(9)  # offset of data in the initial report
_REP_CONT_DATA = const(1)  # offset of data in the continuation report

SESSION_ID = const(0)


class Message:
    def __init__(self, mtype, mdata):
        self.type = mtype
        self.data = mdata


def read_message(iface, buffer):
    read = loop.wait(iface.iface_num() | io.POLL_READ)

    # wait for initial report
    report = yield read
    if report[0] != _REP_MARKER:
        raise ValueError
    _, magic1, magic2, mtype, msize = ustruct.unpack(_REP_INIT, report)
    if magic1 != _REP_MAGIC or magic2 != _REP_MAGIC:
        raise ValueError
    if msize > len(buffer):
        raise ValueError

    # prepare the backing buffer
    mdata = memoryview(buffer)[:msize]

    # buffer the initial data
    nread = utils.memcpy(mdata, 0, report, _REP_INIT_DATA)

    while nread < msize:
        # wait for continuation report
        report = await read
        if report[0] != _REP_MARKER:
            raise ValueError

        # buffer the continuation data
        nread += utils.memcpy(mdata, nread, report, _REP_CONT_DATA)

    return Message(mtype, mdata)


def write_message(iface, msg):
    write = loop.wait(iface.iface_num() | io.POLL_WRITE)

    # gather data from msg
    mtype = msg.type
    mdata = msg.data
    msize = len(mdata)

    # prepare the report buffer with header data
    report = bytearray(_REP_LEN)
    repofs = _REP_INIT_DATA
    ustruct.pack_into(
        _REP_INIT, report, 0, _REP_MARKER, _REP_MAGIC, _REP_MAGIC, mtype, msize
    )

    nwritten = 0
    while True:
        # copy as much as possible to the report buffer
        nwritten += utils.memcpy(report, repofs, mdata, nwritten)

        # write the report
        while True:
            await write
            n = iface.write(report)
            if n == len(report):
                break

        # if we have more data to write, use continuation reports for it
        if nwritten < msize:
            repofs = _REP_CONT_DATA
        else:
            break
