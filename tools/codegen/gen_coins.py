#!/usr/bin/env python3
import json

fields = [
    'coin_name',
    'coin_shortcut',
    'coin_label',
    'address_type',
    'address_type_p2sh',
    'maxfee_kb',
    'signed_message_header',
    'xpub_magic',
    'bech32_prefix',
    'segwit',
    'forkid',
    'force_bip143',
]

coins = json.load(open('../../vendor/trezor-common/coins.json', 'r'))

print('COINS = [')
for c in coins:
    print('    CoinType(')
    for n in fields:
        if n in ['xpub_magic', 'xprv_magic']:
            print('        %s=0x%s,' % (n, c[n]))
        else:
            print('        %s=%s,' % (n, repr(c[n])))
    print('    ),')
print(']\n')
