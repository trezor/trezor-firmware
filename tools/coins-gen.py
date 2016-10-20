#!/usr/bin/env python3
import json
from collections import OrderedDict

coins = json.load(open('../../trezor-common/coins.json', 'r'))

print('_coins = [')
for c in coins:
    d = OrderedDict()
    for n in ['coin_name', 'coin_shortcut', 'maxfee_kb', 'address_type', 'address_type_p2sh', 'address_type_p2wpkh', 'address_type_p2wsh', 'signed_message_header', 'bip44']:
        d[n] = c[n]
    d['xpub_magic'] = int(c['xpub_magic'], 16)
    d['xprv_magic'] = int(c['xprv_magic'], 16)
    print('    {', end='')
    for k in d:
        print('%s: %s, ' % (repr(k), repr(d[k])), end='')
    print('},')
print(']\n')
