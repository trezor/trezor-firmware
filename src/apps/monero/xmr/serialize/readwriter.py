import gc


class MemoryReaderWriter:
    def __init__(
        self,
        buffer=None,
        read_empty=False,
        threshold=None,
        do_gc=False,
        preallocate=None,
        **kwargs
    ):
        self.buffer = buffer
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
        elif self.buffer is None:
            self.buffer = bytearray(0)
        else:
            self.woffset = len(buffer)

    def is_empty(self):
        return self.offset == len(self.buffer) or self.offset == self.woffset

    def preallocate(self, size):
        self.buffer = bytearray(size)
        self.offset = 0
        self.woffset = 0

    def readinto(self, buf):
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

    async def areadinto(self, buf):
        return self.readinto(buf)

    def write(self, buf):
        nwritten = len(buf)
        nall = len(self.buffer)
        towrite = nwritten
        bufoff = 0

        # Fill existing place in the buffer
        while towrite > 0 and nall - self.woffset > 0:
            self.buffer[self.woffset] = buf[bufoff]
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

            self.buffer.extend(chunk)
            if self.do_gc:
                chunk = None  # dereference
                gc.collect()

        self.nwritten += nwritten
        self.ndata += nwritten
        return nwritten

    async def awrite(self, buf):
        return self.write(buf)

    def get_buffer(self):
        mv = memoryview(self.buffer)
        return mv[self.offset : self.woffset]
