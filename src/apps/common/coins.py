from apps.common.coininfo import COINS


def by_shortcut(shortcut):
    for c in COINS:
        if c.coin_shortcut == shortcut:
            return c
    raise ValueError('Unknown coin shortcut "%s"' % shortcut)


def by_name(name):
    for c in COINS:
        if c.coin_name == name:
            return c
    raise ValueError('Unknown coin name "%s"' % name)


def by_address_type(address_type):
    for c in COINS:
        if c.address_type == address_type:
            return c
    raise ValueError('Unknown coin address type %d' % address_type)


def by_slip44(slip44):
    for c in COINS:
        if c.slip44 == slip44:
            return c
    raise ValueError('Unknown coin slip44 index %d' % slip44)
