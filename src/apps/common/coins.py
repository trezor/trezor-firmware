# the following list is generated using tools/coins-gen.py
_coins = [
    {
        'coin_name': 'Bitcoin',
        'coin_shortcut': 'BTC',
        'maxfee_kb': 100000,
        'address_type': 0,
        'address_type_p2sh': 5,
        'address_type_p2wpkh': 6,
        'address_type_p2wsh': 10,
        'signed_message_header': 'Bitcoin Signed Message:\n',
        'bip44': 0,
        'xpub_magic': 76067358,
        'xprv_magic': 76066276,
    },
    {
        'coin_name': 'Testnet',
        'coin_shortcut': 'TEST',
        'maxfee_kb': 10000000,
        'address_type': 111,
        'address_type_p2sh': 196,
        'address_type_p2wpkh': 3,
        'address_type_p2wsh': 40,
        'signed_message_header': 'Bitcoin Signed Message:\n',
        'bip44': 1,
        'xpub_magic': 70617039,
        'xprv_magic': 70615956,
    },
    {
        'coin_name': 'Namecoin',
        'coin_shortcut': 'NMC',
        'maxfee_kb': 10000000,
        'address_type': 52,
        'address_type_p2sh': 5,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'Namecoin Signed Message:\n',
        'bip44': 7,
        'xpub_magic': 27108450,
        'xprv_magic': 27106558,
    },
    {
        'coin_name': 'Litecoin',
        'coin_shortcut': 'LTC',
        'maxfee_kb': 1000000,
        'address_type': 48,
        'address_type_p2sh': 5,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'Litecoin Signed Message:\n',
        'bip44': 2,
        'xpub_magic': 27108450,
        'xprv_magic': 27106558,
    },
    {
        'coin_name': 'Dogecoin',
        'coin_shortcut': 'DOGE',
        'maxfee_kb': 1000000000,
        'address_type': 30,
        'address_type_p2sh': 22,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'Dogecoin Signed Message:\n',
        'bip44': 3,
        'xpub_magic': 49990397,
        'xprv_magic': 49988504,
    },
    {
        'coin_name': 'Dash',
        'coin_shortcut': 'DASH',
        'maxfee_kb': 100000,
        'address_type': 76,
        'address_type_p2sh': 16,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'DarkCoin Signed Message:\n',
        'bip44': 5,
        'xpub_magic': 50221772,
        'xprv_magic': 50221816,
    },
    {
        'coin_name': 'Zcash',
        'coin_shortcut': 'ZEC',
        'maxfee_kb': 1000000,
        'address_type': 7352,
        'address_type_p2sh': 7357,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'Zcash Signed Message:\n',
        'bip44': 133,
        'xpub_magic': 76067358,
        'xprv_magic': 76066276,
    },
    {
        'coin_name': 'Zcash Testnet',
        'coin_shortcut': 'TAZ',
        'maxfee_kb': 10000000,
        'address_type': 7461,
        'address_type_p2sh': 7354,
        'address_type_p2wpkh': None,
        'address_type_p2wsh': None,
        'signed_message_header': 'Zcash Signed Message:\n',
        'bip44': 1,
        'xpub_magic': 70617039,
        'xprv_magic': 70615956,
    },
]


def by_shortcut(shortcut):
    for c in _coins:
        if c['coin_shortcut'] == shortcut:
            return c
    raise Exception('Unknown coin shortcut "%s"' % shortcut)


def by_name(name):
    for c in _coins:
        if c['coin_name'] == name:
            return c
    raise Exception('Unknown coin name "%s"' % name)


def by_address_type(version):
    for c in _coins:
        if c['address_type'] == version:
            return c
    raise Exception('Unknown coin address type %d' % version)
