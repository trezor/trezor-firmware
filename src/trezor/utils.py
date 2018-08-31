import gc
import sys
from trezorutils import (  # noqa: F401
    EMULATOR,
    GITREV,
    MODEL,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    halt,
    memcpy,
    set_mode_unprivileged,
)


def unimport_begin():
    return set(sys.modules)


def unimport_end(mods):
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
            if path in sys.modules:
                delattr(sys.modules[path], name)
    # collect removed modules
    gc.collect()


def ensure(cond, msg=None):
    if not cond:
        if msg is None:
            raise AssertionError()
        else:
            raise AssertionError(msg)


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def split_words(sentence, width, metric=len):
    line = []
    for w in sentence.split(" "):
        # empty word  -> skip
        if not w:
            continue
        # new word will not fit -> break the line
        if metric(" ".join(line + [w])) >= width:
            yield " ".join(line)
            line = []
        # word is too wide -> split the word
        while metric(w) >= width:
            for i in range(1, len(w) + 1):
                if metric(w[:-i]) < width:
                    yield w[:-i] + "-"
                    w = w[-i:]
                    break
        line.append(w)
    yield " ".join(line)


def format_amount(amount, decimals):
    d = pow(10, decimals)
    amount = ("%d.%0*d" % (amount // d, decimals, amount % d)).rstrip("0")
    if amount.endswith("."):
        amount = amount[:-1]
    return amount


def format_ordinal(number):
    return str(number) + {1: "st", 2: "nd", 3: "rd"}.get(
        4 if 10 <= number % 100 < 20 else number % 10, "th"
    )


class HashWriter:
    def __init__(self, hashfunc, *hashargs, **hashkwargs):
        self.ctx = hashfunc(*hashargs, **hashkwargs)
        self.buf = bytearray(1)  # used in append()

    def extend(self, buf: bytearray):
        self.ctx.update(buf)

    def append(self, b: int):
        self.buf[0] = b
        self.ctx.update(self.buf)

    def get_digest(self) -> bytes:
        return self.ctx.digest()
