import struct
from micropython import const
from typing import TYPE_CHECKING

from trezor import io, loop, utils
from trezor.wire.protocol_common import Message, ReadCancelled, WireError

if TYPE_CHECKING:
    from typing import Callable

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


async def read_message(
    iface: WireInterface,
    buffers: CodecBufferSource,
    continuation_timeout_ms: int | None = None,
    abandon_if: "Callable[[], bool] | None" = None,
) -> Message:
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

    mdata: AnyBuffer
    # WHO GIVES THE RECEIVE BUFFER BACK, and None when nobody does -- the two tiers below the
    # pool are private to this message and have nothing shared behind them.
    owner: CodecBufferSource | None = None
    # EVERY REFUSAL IS DEFERRED UNTIL THE MESSAGE HAS BEEN DRAINED, and this is what remembers
    # which one to raise. Refusing early is what the caller sees as a desynchronised interface:
    # the initial report has already been consumed above, so returning now would leave this
    # message's continuation reports on the wire and the next read would parse one of them as a
    # header. The oversize path below has always drained for exactly that reason; contention and
    # the hard size bound have to do the same.
    refusal: WireError | None = None

    if msize > buffers.max_message_size():
        # ABOVE WHAT THIS INTERFACE WILL EVER ACCEPT. Not a pool question -- nothing is allocated
        # for it, so an unauthenticated endpoint cannot turn an advertised length into memory.
        mdata = bytearray(iface.RX_PACKET_LEN)
        refusal = CodecError("Message too large")
    elif msize <= buffers.capacity():
        buf = buffers.get(msize)
        if buf is None:
            # The shared buffer is held by another message in flight. The exception should be
            # caught and handled by the session task: it does not terminate the current session,
            # so an error response can still be sent.
            mdata = bytearray(iface.RX_PACKET_LEN)
            refusal = WireError("Another session in progress")
        else:
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
            refusal = CodecError("Message too large")

    # THE LEASE OUTLIVES THIS FUNCTION ONLY IF THE MESSAGE DOES. Reassembly can still fail on a
    # bad continuation report, and a lease left behind by a message nobody will ever decode is
    # indistinguishable from the per-session ownership this replaced -- except that it never ends.
    try:
        # buffer the initial data
        nread = utils.memcpy(mdata, 0, report, _REP_INIT_DATA)

        # A HEADER IS A PROMISE OF MORE, AND THIS IS HOW LONG THE PEER IS HELD TO IT. Only from
        # here: waiting for a message to BEGIN is what an idle interface does all day and must stay
        # unbounded, while waiting for the rest of one already in progress is a peer failing to
        # finish what it started. The same split, for the same reason, as `apps.webauthn.fido2`,
        # which leaves its initial read unbounded and sets `timeout_ms` once it has a header.
        #
        # `None` means no bound, which is what every host-driven wallet interface has always had.
        if continuation_timeout_ms is not None:
            read.timeout_ms = continuation_timeout_ms

        while nread < msize:
            # wait for continuation report
            try:
                msg_len = await read
            except loop.Timeout:
                # ABANDONED, NOT DRAINED, and the difference matters. Everything else in this
                # function refuses a message it has read to the end, so the wire is left at a
                # boundary; there is nothing to drain here, because the rest never came. The next
                # read starts on whatever arrives next, and a stray continuation report from this
                # message fails the magic check above rather than being mistaken for a header.
                raise CodecError("Message abandoned mid-frame")
            assert msg_len == len(report)
            iface.read(report, 0)
            if report[0] != _REP_MARKER:
                raise CodecError("Invalid magic")

            # ASKED AFTER EVERY REPORT, not only when one fails to arrive. The timeout above
            # bounds a peer that goes quiet; this bounds one that keeps talking after whoever
            # wanted this message has given up on it. Without it a trickle just inside the
            # timeout holds the receive buffer for as long as the peer cares to.
            if abandon_if is not None and abandon_if():
                raise ReadCancelled("Message abandoned by the reader")

            # buffer the continuation data
            if refusal is not None:
                nread += len(report) - 1
            else:
                nread += utils.memcpy(mdata, nread, report, _REP_CONT_DATA)

        if refusal is not None:
            # Drained, so the wire is back at a message boundary and the next read starts on a
            # real header. Only now is it safe to tell the caller.
            raise refusal
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
