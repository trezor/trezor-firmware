import gc


class MemoryReaderWriter:
    def __init__(
        self,
        buffer: bytearray | memoryview | None = None,
        read_empty: bool = False,
        threshold: int | None = None,
        do_gc: bool = False,
        preallocate: int | None = None,
    ) -> None:
        self.nread = 0
        self.nwritten = 0

        self.ndata = 0
        self.offset = 0
        self.woffset = 0

        self.read_empty = read_empty
        self.threshold = threshold
        self.do_gc = do_gc

        if preallocate is not None:
            self.preallocate(preallocate)
        elif buffer is None:
            self.buffer = bytearray(0)
        else:
            self.buffer = buffer
            self.woffset = len(buffer)

    def preallocate(self, size: int) -> None:
        self.buffer = bytearray(size)
        self.offset = 0
        self.woffset = 0

    def readinto(self, buf: bytearray | memoryview) -> int:
        ln = len(buf)
        if not self.read_empty and ln > 0 and self.offset == len(self.buffer):
            raise EOFError

        nread = min(ln, len(self.buffer) - self.offset)
        for idx in range(nread):
            buf[idx] = self.buffer[self.offset + idx]

        self.offset += nread
        self.nread += nread
        self.ndata -= nread

        # Deallocation threshold triggered
        if self.threshold is not None and self.offset >= self.threshold:
            self.buffer = self.buffer[self.offset :]
            self.woffset -= self.offset
            self.offset = 0

            if self.do_gc:
                gc.collect()

        return nread

    def write(self, buf: bytes) -> None:
        buffer = self.buffer  # local_cache_attribute

        assert isinstance(buffer, bytearray)
        nwritten = len(buf)
        nall = len(buffer)
        towrite = nwritten
        bufoff = 0

        # Fill existing place in the buffer
        while towrite > 0 and nall - self.woffset > 0:
            buffer[self.woffset] = buf[bufoff]
            self.woffset += 1
            bufoff += 1
            towrite -= 1

        # Allocate next chunk if needed
        while towrite > 0:
            _towrite = min(32, towrite)
            chunk = bytearray(32)  # chunk size typical for EC point

            for i in range(_towrite):
                chunk[i] = buf[bufoff]
                self.woffset += 1
                bufoff += 1
                towrite -= 1

            buffer.extend(chunk)
            if self.do_gc:
                chunk = None  # dereference
                gc.collect()

        self.nwritten += nwritten
        self.ndata += nwritten
        # return nwritten

    def get_buffer(self) -> bytes:
        mv = memoryview(self.buffer)
        return mv[self.offset : self.woffset]
