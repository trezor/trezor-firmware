import gc
import sys
from trezorutils import (  # noqa: F401
    BITCOIN_ONLY,
    EMULATOR,
    INTERNAL_MODEL,
    MODEL,
    MODEL_FULL_NAME,
    SCM_REVISION,
    UI_LAYOUT,
    USE_BACKLIGHT,
    USE_OPTIGA,
    USE_SD_CARD,
    VERSION,
    bootloader_locked,
    check_firmware_header,
    consteq,
    firmware_hash,
    firmware_vendor,
    halt,
    memcpy,
    reboot_to_bootloader,
    unit_btconly,
    unit_color,
)
from typing import TYPE_CHECKING

# Will get replaced by "True" / "False" in the build process
# However, needs to stay as an exported symbol for the unit tests
MODEL_IS_T2B1: bool = INTERNAL_MODEL == "T2B1"

DISABLE_ANIMATION = 0

if __debug__:
    if EMULATOR:
        import uos

        DISABLE_ANIMATION = int(uos.getenv("TREZOR_DISABLE_ANIMATION") or "0")
        LOG_MEMORY = int(uos.getenv("TREZOR_LOG_MEMORY") or "0")
    else:
        LOG_MEMORY = 0

if TYPE_CHECKING:
    from typing import Any, Iterator, Protocol, Sequence, TypeVar

    from trezor.protobuf import MessageType


def unimport_begin() -> set[str]:
    return set(sys.modules)


def unimport_end(mods: set[str], collect: bool = True) -> None:
    # static check that the size of sys.modules never grows above value of
    # MICROPY_LOADED_MODULES_DICT_SIZE, so that the sys.modules dict is never
    # reallocated at run-time
    assert len(sys.modules) <= 160, "Please bump preallocated size in mpconfigport.h"

    for mod in sys.modules:  # pylint: disable=consider-using-dict-items
        if mod not in mods:
            # remove reference from sys.modules
            del sys.modules[mod]
            # remove reference from the parent module
            i = mod.rfind(".")
            if i < 0:
                continue
            path = mod[:i]
            name = mod[i + 1 :]
            try:
                delattr(sys.modules[path], name)
            except KeyError:
                # either path is not present in sys.modules, or module is not
                # referenced from the parent package. both is fine.
                pass
    # collect removed modules
    if collect:
        gc.collect()


class unimport:
    def __init__(self) -> None:
        self.mods: set[str] | None = None

    def __enter__(self) -> None:
        self.mods = unimport_begin()

    def __exit__(self, _exc_type: Any, _exc_value: Any, _tb: Any) -> None:
        assert self.mods is not None
        unimport_end(self.mods, collect=False)
        self.mods.clear()
        self.mods = None
        gc.collect()


def presize_module(modname: str, size: int) -> None:
    """Ensure the module's dict is preallocated to an expected size.

    This is used in modules like `trezor`, whose dict size depends not only on the
    symbols defined in the file itself, but also on the number of submodules that will
    be inserted into the module's namespace.
    """
    module = sys.modules[modname]
    for i in range(size):
        setattr(module, f"___PRESIZE_MODULE_{i}", None)
    for i in range(size):
        delattr(module, f"___PRESIZE_MODULE_{i}")


if __debug__:

    def mem_dump(filename: str) -> None:
        from micropython import mem_info

        print(f"### sysmodules ({len(sys.modules)}):")
        for mod in sys.modules:
            print("*", mod)
        if EMULATOR:
            from trezorutils import meminfo

            print("### dumping to", filename)
            meminfo(filename)
            mem_info()
        else:
            mem_info(True)


def ensure(cond: bool, msg: str | None = None) -> None:
    if not cond:
        if msg is None:
            raise AssertionError
        else:
            raise AssertionError(msg)


if TYPE_CHECKING:
    Chunkable = TypeVar("Chunkable", str, Sequence[Any])


def chunks(items: Chunkable, size: int) -> Iterator[Chunkable]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


if TYPE_CHECKING:

    class HashContext(Protocol):
        def update(self, __buf: bytes) -> None:
            ...

        def digest(self) -> bytes:
            ...

    class HashContextInitable(HashContext, Protocol):
        def __init__(  # pylint: disable=super-init-not-called
            self, __data: bytes | None = None
        ) -> None:
            ...

    class Writer(Protocol):
        def append(self, __b: int) -> None:
            ...

        def extend(self, __buf: bytes) -> None:
            ...


if False:  # noqa

    class DebugHashContextWrapper:
        """
        Use this wrapper to debug hashing operations. When digest() is called,
        it will log all of the data that was provided to update().

        Example usage:
        self.h_prevouts = HashWriter(DebugHashContextWrapper(sha256()))
        """

        def __init__(self, ctx: HashContext) -> None:
            self.ctx = ctx
            self.data = ""

        def update(self, data: bytes) -> None:
            from ubinascii import hexlify

            self.ctx.update(data)
            self.data += hexlify(data).decode() + " "

        def digest(self) -> bytes:
            from ubinascii import hexlify

            from trezor import log

            digest = self.ctx.digest()
            log.debug(
                __name__,
                "%s hash: %s, data: %s",
                self.ctx.__class__.__name__,
                hexlify(digest).decode(),
                self.data,
            )
            return digest


class HashWriter:
    def __init__(self, ctx: HashContext) -> None:
        self.ctx = ctx
        self.buf = bytearray(1)  # used in append()

    def append(self, b: int) -> None:
        self.buf[0] = b
        self.ctx.update(self.buf)

    def extend(self, buf: bytes) -> None:
        self.ctx.update(buf)

    def write(self, buf: bytes) -> None:  # alias for extend()
        self.ctx.update(buf)

    def get_digest(self) -> bytes:
        return self.ctx.digest()


if TYPE_CHECKING:
    BufferType = bytearray | memoryview


class BufferReader:
    """Seekable and readable view into a buffer."""

    def __init__(self, buffer: bytes | memoryview) -> None:
        if isinstance(buffer, memoryview):
            self.buffer = buffer
        else:
            self.buffer = memoryview(buffer)
        self.offset = 0

    def seek(self, offset: int) -> None:
        """Set current offset to `offset`.

        If negative, set to zero. If longer than the buffer, set to end of buffer.
        """
        offset = min(offset, len(self.buffer))
        offset = max(offset, 0)
        self.offset = offset

    def readinto(self, dst: BufferType) -> int:
        """Read exactly `len(dst)` bytes into `dst`, or raise EOFError.

        Returns number of bytes read.
        """
        buffer = self.buffer
        offset = self.offset
        if len(dst) > len(buffer) - offset:
            raise EOFError
        nread = memcpy(dst, 0, buffer, offset)
        self.offset += nread
        return nread

    def read(self, length: int | None = None) -> bytes:
        """Read and return exactly `length` bytes, or raise EOFError.

        If `length` is unspecified, reads all remaining data.

        Note that this method makes a copy of the data. To avoid allocation, use
        `readinto()`. To avoid copying use `read_memoryview()`.
        """
        return bytes(self.read_memoryview(length))

    def read_memoryview(self, length: int | None = None) -> memoryview:
        """Read and return a memoryview of exactly `length` bytes, or raise
        EOFError.

        If `length` is unspecified, reads all remaining data.
        """
        if length is None:
            ret = self.buffer[self.offset :]
            self.offset = len(self.buffer)
        elif length < 0:
            raise ValueError
        elif length <= self.remaining_count():
            ret = self.buffer[self.offset : self.offset + length]
            self.offset += length
        else:
            raise EOFError
        return ret

    def remaining_count(self) -> int:
        """Return the number of bytes remaining for reading."""
        return len(self.buffer) - self.offset

    def peek(self) -> int:
        """Peek the ordinal value of the next byte to be read."""
        if self.offset >= len(self.buffer):
            raise EOFError
        return self.buffer[self.offset]

    def get(self) -> int:
        """Read exactly one byte and return its ordinal value."""
        if self.offset >= len(self.buffer):
            raise EOFError
        byte = self.buffer[self.offset]
        self.offset += 1
        return byte


def obj_eq(self: Any, __o: Any) -> bool:
    """
    Compares object contents.
    """
    if self.__class__ is not __o.__class__:
        return False
    assert not hasattr(self, "__slots__")
    return self.__dict__ == __o.__dict__


def obj_repr(self: Any) -> str:
    """
    Returns a string representation of object.
    """
    assert not hasattr(self, "__slots__")
    return f"<{self.__class__.__name__}: {self.__dict__}>"


def truncate_utf8(string: str, max_bytes: int) -> str:
    """Truncate the codepoints of a string so that its UTF-8 encoding is at most `max_bytes` in length."""
    data = string.encode()
    if len(data) <= max_bytes:
        return string

    # Find the starting position of the last codepoint in data[0 : max_bytes + 1].
    i = max_bytes
    while i >= 0 and data[i] & 0xC0 == 0x80:
        i -= 1

    return data[:i].decode()


def is_empty_iterator(i: Iterator) -> bool:
    try:
        next(i)
    except StopIteration:
        return True
    else:
        return False


def empty_bytearray(preallocate: int) -> bytearray:
    """
    Returns bytearray that won't allocate for at least `preallocate` bytes.
    Useful in case you want to avoid allocating too often.
    """
    b = bytearray(preallocate)
    b[:] = bytes()
    return b


if __debug__:

    def dump_protobuf_lines(msg: MessageType, line_start: str = "") -> Iterator[str]:
        msg_dict = msg.__dict__
        if not msg_dict:
            yield line_start + msg.MESSAGE_NAME + " {}"
            return

        yield line_start + msg.MESSAGE_NAME + " {"
        for key, val in msg_dict.items():
            if type(val) == type(msg):
                sublines = dump_protobuf_lines(val, line_start=key + ": ")
                for subline in sublines:
                    yield "    " + subline
            elif val and isinstance(val, list) and type(val[0]) == type(msg):
                # non-empty list of protobuf messages
                yield f"    {key}: ["
                for subval in val:
                    sublines = dump_protobuf_lines(subval)
                    for subline in sublines:
                        yield "        " + subline
                yield "    ]"
            else:
                yield f"    {key}: {repr(val)}"

        yield "}"

    def dump_protobuf(msg: MessageType) -> str:
        return "\n".join(dump_protobuf_lines(msg))
