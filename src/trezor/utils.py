import sys
import gc

from trezorutils import halt, memcpy, set_mode_unprivileged


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


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def ensure(cond):
    if not cond:
        raise AssertionError()


def format_amount(amount, decimals):
    d = pow(10, decimals)
    amount = ('%d.%0*d' % (amount // d, decimals, amount % d)).rstrip('0')
    if amount.endswith('.'):
        amount = amount[:-1]
    return amount
