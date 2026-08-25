import struct
from micropython import const
from typing import TYPE_CHECKING

from trezor import io, loop, utils
from trezor.wire.protocol_common import Message, WireError

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from trezorio import WireInterface

    from .buffers import CodecBufferSource

_REP_MARKER = const(63)  # ord('?')
_REP_MAGIC = const(35)  # org('#')
_REP_INIT = ">BBBHL"  # marker, magic, magic, wire type, data length
_REP_INIT_DATA = const(9)  # offset of data in the initial report
_REP_CONT_DATA = const(1)  # offset of data in the continuation report


class CodecError(WireError):
    pass


async def read_message(iface: WireInterface, buffers: CodecBufferSource) -> Message:
    read = loop.wait(iface.iface_num() | io.POLL_READ)
    report = bytearray(iface.RX_PACKET_LEN)

    # wait for initial report
    msg_len = await read
    assert msg_len == len(report)
    iface.read(report, 0)
    if report[0] != _REP_MARKER:
        raise CodecError("Invalid magic")
    _, magic1, magic2, mtype, msize = struct.unpack(_REP_INIT, report)
    if magic1 != _REP_MAGIC or magic2 != _REP_MAGIC:
        raise CodecError("Invalid magic")

    read_and_throw_away = False
    mdata: AnyBuffer
    # WHO GIVES THE RECEIVE BUFFER BACK, and None when nobody does -- the two tiers below the
    # pool are private to this message and have nothing shared behind them.
    owner: CodecBufferSource | None = None

    if msize <= buffers.capacity():
        buf = buffers.get(msize)
        if buf is None:
            # The shared buffer is held by another message in flight. The exception should be
            # caught and handled by the session task: it does not terminate the current session,
            # so an error response can still be sent.
            raise WireError("Another session in progress")
        mdata = buf
        owner = buffers
    else:
        # TOO LARGE FOR THE POOL, which is not the same as too large to handle and never was.
        # Allocate for it, and if even that fails, read the message off the wire and refuse it --
        # leaving it half-read would desynchronise every message after it.
        try:
            mdata = bytearray(msize)
        except MemoryError:
            mdata = bytearray(iface.RX_PACKET_LEN)
            read_and_throw_away = True

    # THE LEASE OUTLIVES THIS FUNCTION ONLY IF THE MESSAGE DOES. Reassembly can still fail on a
    # bad continuation report, and a lease left behind by a message nobody will ever decode is
    # indistinguishable from the per-session ownership this replaced -- except that it never ends.
    try:
        # buffer the initial data
        nread = utils.memcpy(mdata, 0, report, _REP_INIT_DATA)

        while nread < msize:
            # wait for continuation report
            msg_len = await read
            assert msg_len == len(report)
            iface.read(report, 0)
            if report[0] != _REP_MARKER:
                raise CodecError("Invalid magic")

            # buffer the continuation data
            if read_and_throw_away:
                nread += len(report) - 1
            else:
                nread += utils.memcpy(mdata, nread, report, _REP_CONT_DATA)

        if read_and_throw_away:
            raise CodecError("Message too large")
    except BaseException:
        if owner is not None:
            owner.release()
        raise

    return Message(mtype, mdata, owner)


async def write_message(iface: WireInterface, mtype: int, mdata: AnyBytes) -> None:
    write = loop.wait(iface.iface_num() | io.POLL_WRITE)

    # gather data from msg
    msize = len(mdata)

    # prepare the report buffer with header data
    report = bytearray(iface.TX_PACKET_LEN)
    repofs = _REP_INIT_DATA
    struct.pack_into(
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
            assert n == 0

        # if we have more data to write, use continuation reports for it
        if nwritten < msize:
            repofs = _REP_CONT_DATA
        else:
            break
