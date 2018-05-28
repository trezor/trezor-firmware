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
    'segwit',
    'fork_id',
    'force_bip143',
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
        if n == 'xpub_magic':
            print('        %s=0x%08x,' % (n, data[n]))
        else:
            print('        %s=%s,' % (n, repr(data[n])))
    print('    ),')

print(']')
