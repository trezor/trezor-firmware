from trezor.utils import memcpy


class StreamReader:

    def __init__(self, buffer=None, limit=None):
        if buffer is None:
            buffer = bytearray()
        self._buffer = buffer
        self._limit = limit
        self._ofs = 0

    async def read_into(self, dst):
        '''
        Read exactly `len(dst)` bytes into writable buffer-like `dst`.

        Raises `EOFError` if the internal limit was reached or the
        backing IO strategy signalled an EOF.
        '''
        n = len(dst)

        if self._limit is not None:
            if self._limit < n:
                raise EOFError()
            self._limit -= n

        buf = self._buffer
        ofs = self._ofs
        i = 0
        while i < n:
            if ofs >= len(buf):
                buf = yield
                ofs = 0
            # memcpy caps on the buffer lengths, no need for exact byte count
            nb = memcpy(dst, i, buf, ofs, n)
            ofs += nb
            i += nb
        self._buffer = buf
        self._ofs = ofs

    def with_limit(self, n):
        '''
        Makes this reader to signal EOF after reading `n` bytes.

        Returns the number of bytes that the reader can read after
        raising EOF (intended to be restored with another call to
        `with_limit`).
        '''
        if self._limit is not None:
            rem = self._limit - n
        else:
            rem = None
        self._limit = n
        return rem


class BufferWriter:

    def __init__(self, buffer=None):
        if buffer is None:
            buffer = bytearray()
        self.buffer = buffer

    async def write(self, b):
        self.buffer.extend(b)
