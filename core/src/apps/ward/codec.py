"""Byte-level helpers every WARD encoding is built from: big-endian integers, length-prefixed
fields, and a strict reader. One place for the framing, so no encoder hand-rolls its offsets."""


def u32(n: int) -> bytes:
    return n.to_bytes(4, "big")


def lp(width: int, data: bytes, error: str) -> bytes:
    """`len(data)` in `width` bytes, then `data`; DataError(error) if the length does not fit."""
    from trezor.wire import DataError

    if len(data) >> (8 * width):
        raise DataError(error)
    return len(data).to_bytes(width, "big") + data


def step_bytes(
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
) -> bytes:
    """from_counter(4) || from_root(32) || to_counter(4) || to_root(32), roots in preimage form."""
    from .attest import root_or_empty

    return u32(from_counter) + root_or_empty(from_root) + u32(to_counter) + root_or_empty(to_root)


class Reader:
    """Reads fields off `data` from `off`, raising DataError(error) on any short read."""

    def __init__(self, data: bytes, off: int = 0, error: str = "WARD: truncated record") -> None:
        self.data = data
        self.off = off
        self.error = error

    def take(self, n: int) -> bytes:
        from trezor.wire import DataError

        chunk = self.data[self.off : self.off + n]
        # a slice past the end is short, not an error: check every width
        if len(chunk) != n:
            raise DataError(self.error)
        self.off += n
        return chunk

    def uint(self, width: int) -> int:
        return int.from_bytes(self.take(width), "big")

    def lp(self, width: int) -> bytes:
        return self.take(self.uint(width))

    def done(self) -> bool:
        return self.off == len(self.data)
