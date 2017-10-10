from micropython import const
import ustruct

from trezor import io
from trezor import loop
from trezor import utils
from trezor.crypto import random

# TREZOR wire protocol #2:
#
# # Initial message report
# uint8_t  marker;        // REP_MARKER_INIT
# uint32_t session_id;    // Big-endian
# uint32_t message_type;  // Big-endian
# uint32_t message_size;  // Big-endian
# uint8_t  data[];
#
# # Continuation message report
# uint8_t  marker;      // REP_MARKER_CONT
# uint32_t session_id;  // Big-endian
# uint32_t sequence;    // Big-endian, 0 for 1st continuation report
# uint8_t  data[];

_REP_LEN = const(64)

_REP_MARKER_INIT = const(0x01)
_REP_MARKER_CONT = const(0x02)
_REP_MARKER_OPEN = const(0x03)
_REP_MARKER_CLOSE = const(0x04)

_REP = '>BL'  # marker, session_id
_REP_INIT = '>BLLL'  # marker, session_id, message_type, message_size
_REP_CONT = '>BLL'  # marker, session_id, sequence
_REP_INIT_DATA = const(13)  # offset of data in init report
_REP_CONT_DATA = const(9)  # offset of data in cont report


class Reader:
    '''
    Decoder for v2 codec over the HID layer.  Provides readable async-file-like
    interface.
    '''

    def __init__(self, iface, sid):
        self.iface = iface
        self.sid = sid
        self.type = None
        self.size = None
        self.data = None
        self.ofs = 0
        self.seq = 0

    def __repr__(self):
        return '<Reader: sid=%x type=%d size=%dB>' % (self.sid, self.type,
                                                      self.size)

    async def aopen(self):
        '''
        Begin the message transmission by waiting for initial V2 message report
        on this session. `self.type` and `self.size` are initialized and
        available after `aopen()` returns.
        '''
        read = loop.select(self.iface.iface_num() | io.POLL_READ)
        while True:
            # wait for initial report
            report = await read
            marker, sid, mtype, msize = ustruct.unpack(_REP_INIT, report)
            if sid == self.sid and marker == _REP_MARKER_INIT:
                break

        # load received message header
        self.type = mtype
        self.size = msize
        self.data = report[_REP_INIT_DATA:_REP_INIT_DATA + msize]
        self.ofs = 0
        self.seq = 0

    async def areadinto(self, buf):
        '''
        Read exactly `len(buf)` bytes into `buf`, waiting for additional
        reports, if needed.  Raises `EOFError` if end-of-message is encountered
        before the full read can be completed.
        '''
        if self.size < len(buf):
            raise EOFError

        read = loop.select(self.iface.iface_num() | io.POLL_READ)
        nread = 0
        while nread < len(buf):
            if self.ofs == len(self.data):
                # we are at the end of received data
                # wait for continuation report
                while True:
                    report = await read
                    marker, sid, seq = ustruct.unpack(_REP_CONT, report)
                    if sid == self.sid and marker == _REP_MARKER_CONT:
                        if seq != self.seq:
                            raise ValueError
                        break
                self.data = report[_REP_CONT_DATA:_REP_CONT_DATA + self.size]
                self.seq += 1
                self.ofs = 0

            # copy as much as possible to target buffer
            nbytes = utils.memcpy(buf, nread, self.data, self.ofs, len(buf))
            nread += nbytes
            self.ofs += nbytes
            self.size -= nbytes

        return nread


class Writer:
    '''
    Encoder for v2 codec over the HID layer.  Provides writable async-file-like
    interface.
    '''

    def __init__(self, iface, sid):
        self.iface = iface
        self.sid = sid
        self.type = None
        self.size = None
        self.data = bytearray(_REP_LEN)
        self.ofs = 0
        self.seq = 0

    def __repr__(self):
        return '<WriterV2: type=%d size=%dB>' % (self.type, self.size)

    def setheader(self, mtype, msize):
        '''
        Reset the writer state and load the message header with passed type and
        total message size.
        '''
        self.type = mtype
        self.size = msize
        ustruct.pack_into(_REP_INIT, self.data, 0, _REP_MARKER_INIT, self.sid,
                          mtype, msize)
        self.ofs = _REP_INIT_DATA
        self.seq = 0

    async def awrite(self, buf):
        '''
        Encode and write every byte from `buf`.  Does not need to be called in
        case message has zero length.  Raises `EOFError` if the length of `buf`
        exceeds the remaining message length.
        '''
        if self.size < len(buf):
            raise EOFError

        write = loop.select(self.iface.iface_num() | io.POLL_WRITE)
        nwritten = 0
        while nwritten < len(buf):
            # copy as much as possible to report buffer
            nbytes = utils.memcpy(self.data, self.ofs, buf, nwritten, len(buf))
            nwritten += nbytes
            self.ofs += nbytes
            self.size -= nbytes

            if self.ofs == _REP_LEN:
                # we are at the end of the report, flush it, and prepare header
                await write
                self.iface.write(self.data)
                ustruct.pack_into(_REP_CONT, self.data, 0, _REP_MARKER_CONT,
                                  self.sid, self.seq)
                self.ofs = _REP_CONT_DATA
                self.seq += 1

        return nwritten

    async def aclose(self):
        '''Flush and close the message transmission.'''
        if self.ofs != _REP_CONT_DATA:
            # we didn't write anything or last write() wasn't report-aligned,
            # pad the final report and flush it
            while self.ofs < _REP_LEN:
                self.data[self.ofs] = 0x00
                self.ofs += 1

            await loop.select(self.iface.iface_num() | io.POLL_WRITE)
            self.iface.write(self.data)


class SesssionSupervisor:
    '''Handles session open/close requests on v2 protocol layer.'''

    def __init__(self, iface, handler):
        self.iface = iface
        self.handler = handler
        self.handling_tasks = {}
        self.session_report = bytearray(_REP_LEN)

    async def listen(self):
        '''
        Listen for open/close requests on configured interface.  After open
        request, session is started and a new task is scheduled to handle it.
        After close request, the handling task is closed and session terminated.
        Both requests receive responses confirming the operation.
        '''
        read = loop.select(self.iface.iface_num() | io.POLL_READ)
        write = loop.select(self.iface.iface_num() | io.POLL_WRITE)
        while True:
            report = await read
            repmarker, repsid = ustruct.unpack(_REP, report)
            # because tasks paused on I/O have a priority over time-scheduled
            # tasks, we need to `yield` explicitly before sending a response to
            # open/close request.  Otherwise the handler would have no chance to
            # run and schedule communication.
            if repmarker == _REP_MARKER_OPEN:
                newsid = self.newsid()
                self.open(newsid)
                yield
                await write
                self.writeopen(newsid)
            elif repmarker == _REP_MARKER_CLOSE:
                self.close(repsid)
                yield
                await write
                self.writeclose(repsid)

    def open(self, sid):
        if sid not in self.handling_tasks:
            task = self.handling_tasks[sid] = self.handler(self.iface, sid)
            loop.schedule(task)

    def close(self, sid):
        if sid in self.handling_tasks:
            task = self.handling_tasks.pop(sid)
            loop.close(task)

    def newsid(self):
        while True:
            sid = random.uniform(0xffffffff) + 1
            if sid not in self.handling_tasks:
                return sid

    def writeopen(self, sid):
        ustruct.pack_into(_REP, self.session_report, 0, _REP_MARKER_OPEN, sid)
        self.iface.write(self.session_report)

    def writeclose(self, sid):
        ustruct.pack_into(_REP, self.session_report, 0, _REP_MARKER_CLOSE, sid)
        self.iface.write(self.session_report)
