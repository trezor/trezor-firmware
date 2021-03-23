import ustruct
from micropython import const

from trezor import io, loop, utils

if False:
    from trezorio import WireInterface

_REP_LEN = const(64)

_REP_MARKER = const(63)  # ord('?')
_REP_MAGIC = const(35)  # org('#')
_REP_INIT = ">BBBHL"  # marker, magic, magic, wire type, data length
_REP_INIT_DATA = const(9)  # offset of data in the initial report
_REP_CONT_DATA = const(1)  # offset of data in the continuation report

SESSION_ID = const(0)
INVALID_TYPE = const(-1)


class CodecError(Exception):
    pass


class Message:
    def __init__(self, mtype: int, mdata: bytes) -> None:
        self.type = mtype
        self.data = mdata


async def read_message(iface: WireInterface, buffer: utils.BufferType) -> Message:
    read = loop.wait(iface.iface_num() | io.POLL_READ)

    # wait for initial report
    report = await read
    if report[0] != _REP_MARKER:
        raise CodecError("Invalid magic")
    _, magic1, magic2, mtype, msize = ustruct.unpack(_REP_INIT, report)
    if magic1 != _REP_MAGIC or magic2 != _REP_MAGIC:
        raise CodecError("Invalid magic")

    read_and_throw_away = False

    if msize > len(buffer):
        # allocate a new buffer to fit the message
        try:
            mdata: utils.BufferType = bytearray(msize)
        except MemoryError:
            mdata = bytearray(_REP_LEN)
            read_and_throw_away = True
    else:
        # reuse a part of the supplied buffer
        mdata = memoryview(buffer)[:msize]

    # buffer the initial data
    nread = utils.memcpy(mdata, 0, report, _REP_INIT_DATA)

    while nread < msize:
        # wait for continuation report
        report = await read
        if report[0] != _REP_MARKER:
            raise CodecError("Invalid magic")

        # buffer the continuation data
        if read_and_throw_away:
            nread += len(report) - 1
        else:
            nread += utils.memcpy(mdata, nread, report, _REP_CONT_DATA)

    if read_and_throw_away:
        raise CodecError("Message too large")

    return Message(mtype, mdata)


async def write_message(iface: WireInterface, mtype: int, mdata: bytes) -> None:
    write = loop.wait(iface.iface_num() | io.POLL_WRITE)

    # gather data from msg
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
