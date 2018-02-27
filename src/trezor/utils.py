import sys
import gc

from trezorutils import halt, memcpy, set_mode_unprivileged, symbol  # noqa: F401


def unimport(genfunc):
    async def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = await genfunc(*args, **kwargs)
        finally:
            for mod in sys.modules:
                if mod not in mods:
                    del sys.modules[mod]
            gc.collect()
        return ret
    return inner


def ensure(cond):
    if not cond:
        raise AssertionError()


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def split_words(sentence, width, metric=len):
    line = []
    for w in sentence.split(' '):
        if not w:
            continue
        if metric(' '.join(line + [w])) >= width:
            yield ' '.join(line)
            line = [w]
        else:
            line.append(w)
    yield ' '.join(line)


def format_amount(amount, decimals):
    d = pow(10, decimals)
    amount = ('%d.%0*d' % (amount // d, decimals, amount % d)).rstrip('0')
    if amount.endswith('.'):
        amount = amount[:-1]
    return amount


def format_ordinal(number):
    return str(number) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= number % 100 < 20 else number % 10, 'th')
