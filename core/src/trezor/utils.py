import gc
import sys
from trezorutils import (  # type: ignore[attr-defined] # noqa: F401
    BITCOIN_ONLY,
    EMULATOR,
    GITREV,
    MODEL,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    consteq,
    halt,
    memcpy,
    set_mode_unprivileged,
)

if __debug__:
    if EMULATOR:
        import uos

        TEST = int(uos.getenv("TREZOR_TEST") or "0")
        DISABLE_FADE = int(uos.getenv("TREZOR_DISABLE_FADE") or "0")
        SAVE_SCREEN = int(uos.getenv("TREZOR_SAVE_SCREEN") or "0")
        LOG_MEMORY = int(uos.getenv("TREZOR_LOG_MEMORY") or "0")
    else:
        TEST = 0
        DISABLE_FADE = 0
        SAVE_SCREEN = 0
        LOG_MEMORY = 0

if False:
    from typing import Any, Iterable, Iterator, Protocol, TypeVar, Sequence


def unimport_begin() -> Iterable[str]:
    return set(sys.modules)


def unimport_end(mods: Iterable[str]) -> None:
    for mod in sys.modules:
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
    gc.collect()


def ensure(cond: bool, msg: str = None) -> None:
    if not cond:
        if msg is None:
            raise AssertionError
        else:
            raise AssertionError(msg)


if False:
    Chunkable = TypeVar("Chunkable", str, Sequence[Any])


def chunks(items: Chunkable, size: int) -> Iterator[Chunkable]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def format_amount(amount: int, decimals: int) -> str:
    if amount < 0:
        amount = -amount
        sign = "-"
    else:
        sign = ""
    d = pow(10, decimals)
    s = (
        ("%s%d.%0*d" % (sign, amount // d, decimals, amount % d))
        .rstrip("0")
        .rstrip(".")
    )
    return s


def format_ordinal(number: int) -> str:
    return str(number) + {1: "st", 2: "nd", 3: "rd"}.get(
        4 if 10 <= number % 100 < 20 else number % 10, "th"
    )


if False:

    class HashContext(Protocol):
        def update(self, buf: bytes) -> None:
            ...

        def digest(self) -> bytes:
            ...

    class Writer(Protocol):
        def append(self, b: int) -> None:
            ...

        def extend(self, buf: bytes) -> None:
            ...

        def write(self, buf: bytes) -> None:
            ...


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

    async def awrite(self, buf: bytes) -> int:  # AsyncWriter interface
        self.ctx.update(buf)
        return len(buf)

    def get_digest(self) -> bytes:
        return self.ctx.digest()


def obj_eq(l: object, r: object) -> bool:
    """
    Compares object contents, supports __slots__.
    """
    if l.__class__ is not r.__class__:
        return False
    if not hasattr(l, "__slots__"):
        return l.__dict__ == r.__dict__
    if l.__slots__ is not r.__slots__:
        return False
    for slot in l.__slots__:
        if getattr(l, slot, None) != getattr(r, slot, None):
            return False
    return True


def obj_repr(o: object) -> str:
    """
    Returns a string representation of object, supports __slots__.
    """
    if hasattr(o, "__slots__"):
        d = {attr: getattr(o, attr, None) for attr in o.__slots__}
    else:
        d = o.__dict__
    return "<%s: %s>" % (o.__class__.__name__, d)
