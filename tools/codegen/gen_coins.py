#!/usr/bin/env python3
import json

fields = [
    'coin_name',
    'coin_shortcut',
    'address_type',
    'address_type_p2sh',
    'maxfee_kb',
    'signed_message_header',
    'xpub_magic',
    'bech32_prefix',
    'cashaddr_prefix',
    'slip44',
    'segwit',
    'fork_id',
    'force_bip143',
    'version_group_id',
]

support = json.load(open('../../vendor/trezor-common/defs/support.json', 'r'))
coins = support['trezor2'].keys()

print('COINS = [')

for c in coins:
    print('    CoinInfo(')
    name = c.replace(' ', '_').lower()
    if name == 'testnet':
        name = 'bitcoin_testnet'
    data = json.load(open('../../vendor/trezor-common/defs/coins/%s.json' % name, 'r'))
    for n in fields:
        if n in ['xpub_magic', 'version_group_id']:
            v = '0x%08x' % data[n] if data[n] is not None else 'None'
        else:
            v = repr(data[n])
        print('        %s=%s,' % (n, v))
    print('    ),')

print(']')
