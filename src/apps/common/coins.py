from trezor.messages.CoinType import CoinType

# the following list is generated using tools/coins-gen.py
# do not edit manually!
_coins = [
    CoinType(
        coin_name='Bitcoin',
        coin_shortcut='BTC',
        address_type=0,
        maxfee_kb=100000,
        address_type_p2sh=5,
        address_type_p2wpkh=6,
        address_type_p2wsh=10,
        signed_message_header='Bitcoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Testnet',
        coin_shortcut='TEST',
        address_type=111,
        maxfee_kb=10000000,
        address_type_p2sh=196,
        address_type_p2wpkh=3,
        address_type_p2wsh=40,
        signed_message_header='Bitcoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Namecoin',
        coin_shortcut='NMC',
        address_type=52,
        maxfee_kb=10000000,
        address_type_p2sh=5,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Namecoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Litecoin',
        coin_shortcut='LTC',
        address_type=48,
        maxfee_kb=1000000,
        address_type_p2sh=5,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Litecoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Dogecoin',
        coin_shortcut='DOGE',
        address_type=30,
        maxfee_kb=1000000000,
        address_type_p2sh=22,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Dogecoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Dash',
        coin_shortcut='DASH',
        address_type=76,
        maxfee_kb=100000,
        address_type_p2sh=16,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='DarkCoin Signed Message:\n',
    ),
    CoinType(
        coin_name='Zcash',
        coin_shortcut='ZEC',
        address_type=7352,
        maxfee_kb=1000000,
        address_type_p2sh=7357,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Zcash Signed Message:\n',
    ),
    CoinType(
        coin_name='Zcash Testnet',
        coin_shortcut='TAZ',
        address_type=7461,
        maxfee_kb=10000000,
        address_type_p2sh=7354,
        address_type_p2wpkh=None,
        address_type_p2wsh=None,
        signed_message_header='Zcash Signed Message:\n',
    ),
]


def by_shortcut(shortcut):
    for c in _coins:
        if c.coin_shortcut == shortcut:
            return c
    raise Exception('Unknown coin shortcut "%s"' % shortcut)


def by_name(name):
    for c in _coins:
        if c.coin_name == name:
            return c
    raise Exception('Unknown coin name "%s"' % name)


def by_address_type(version):
    for c in _coins:
        if c.address_type == version:
            return c
    raise Exception('Unknown coin address type %d' % version)
