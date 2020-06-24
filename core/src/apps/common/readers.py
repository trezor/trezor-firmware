if False:
    from typing import Optional


class BytearrayReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def get(self) -> int:
        ret = self.data[self.offset]
        self.offset += 1
        return ret

    def peek(self) -> int:
        return self.data[self.offset]

    def read(self, i: Optional[int] = None) -> bytes:
        if i is None:
            ret = self.data[self.offset :]
            self.offset = len(self.data)
        elif 0 <= i <= len(self.data) - self.offset:
            ret = self.data[self.offset : self.offset + i]
            self.offset += i
        else:
            raise IndexError
        return ret

    def remaining_count(self) -> int:
        return len(self.data) - self.offset


def read_bitcoin_varint(r: BytearrayReader) -> int:
    prefix = r.get()
    if prefix < 253:
        n = prefix
    elif prefix == 253:
        n = r.get()
        n += r.get() << 8
    elif prefix == 254:
        n = r.get()
        n += r.get() << 8
        n += r.get() << 16
        n += r.get() << 24
    else:
        raise ValueError
    return n
