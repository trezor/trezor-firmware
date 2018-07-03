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


class Reader:
    """
    Decoder for legacy codec over the HID layer.  Provides readable
    async-file-like interface.
    """

    def __init__(self, iface):
        self.iface = iface
        self.type = None
        self.size = None
        self.data = None
        self.ofs = 0

    def __repr__(self):
        return "<ReaderV1: type=%d size=%dB>" % (self.type, self.size)

    async def aopen(self):
        """
        Begin the message transmission by waiting for initial V2 message report
        on this session.  `self.type` and `self.size` are initialized and
        available after `aopen()` returns.
        """
        read = loop.wait(self.iface.iface_num() | io.POLL_READ)
        while True:
            # wait for initial report
            report = await read
            marker = report[0]
            if marker == _REP_MARKER:
                _, m1, m2, mtype, msize = ustruct.unpack(_REP_INIT, report)
                if m1 != _REP_MAGIC or m2 != _REP_MAGIC:
                    raise ValueError
                break

        # load received message header
        self.type = mtype
        self.size = msize
        self.data = report[_REP_INIT_DATA : _REP_INIT_DATA + msize]
        self.ofs = 0

    async def areadinto(self, buf):
        """
        Read exactly `len(buf)` bytes into `buf`, waiting for additional
        reports, if needed.  Raises `EOFError` if end-of-message is encountered
        before the full read can be completed.
        """
        if self.size < len(buf):
            raise EOFError

        read = loop.wait(self.iface.iface_num() | io.POLL_READ)
        nread = 0
        while nread < len(buf):
            if self.ofs == len(self.data):
                # we are at the end of received data
                # wait for continuation report
                while True:
                    report = await read
                    marker = report[0]
                    if marker == _REP_MARKER:
                        break
                self.data = report[_REP_CONT_DATA : _REP_CONT_DATA + self.size]
                self.ofs = 0

            # copy as much as possible to target buffer
            nbytes = utils.memcpy(buf, nread, self.data, self.ofs, len(buf))
            nread += nbytes
            self.ofs += nbytes
            self.size -= nbytes

        return nread


class Writer:
    """
    Encoder for legacy codec over the HID layer.  Provides writable
    async-file-like interface.
    """

    def __init__(self, iface):
        self.iface = iface
        self.type = None
        self.size = None
        self.data = bytearray(_REP_LEN)
        self.ofs = 0

    def __repr__(self):
        return "<WriterV1: type=%d size=%dB>" % (self.type, self.size)

    def setheader(self, mtype, msize):
        """
        Reset the writer state and load the message header with passed type and
        total message size.
        """
        self.type = mtype
        self.size = msize
        ustruct.pack_into(
            _REP_INIT, self.data, 0, _REP_MARKER, _REP_MAGIC, _REP_MAGIC, mtype, msize
        )
        self.ofs = _REP_INIT_DATA

    async def awrite(self, buf):
        """
        Encode and write every byte from `buf`.  Does not need to be called in
        case message has zero length.  Raises `EOFError` if the length of `buf`
        exceeds the remaining message length.
        """
        if self.size < len(buf):
            raise EOFError

        write = loop.wait(self.iface.iface_num() | io.POLL_WRITE)
        nwritten = 0
        while nwritten < len(buf):
            # copy as much as possible to report buffer
            nbytes = utils.memcpy(self.data, self.ofs, buf, nwritten, len(buf))
            nwritten += nbytes
            self.ofs += nbytes
            self.size -= nbytes

            if self.ofs == _REP_LEN:
                # we are at the end of the report, flush it
                while True:
                    await write
                    n = self.iface.write(self.data)
                    if n == len(self.data):
                        break
                self.ofs = _REP_CONT_DATA

        return nwritten

    async def aclose(self):
        """Flush and close the message transmission."""
        if self.ofs != _REP_CONT_DATA:
            # we didn't write anything or last write() wasn't report-aligned,
            # pad the final report and flush it
            while self.ofs < _REP_LEN:
                self.data[self.ofs] = 0x00
                self.ofs += 1

            write = loop.wait(self.iface.iface_num() | io.POLL_WRITE)
            while True:
                await write
                n = self.iface.write(self.data)
                if n == len(self.data):
                    break
