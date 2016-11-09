#!/usr/bin/env python3
import json
from collections import OrderedDict

coins = json.load(open('../../trezor-common/coins.json', 'r'))

print('_coins = [')
for c in coins:
    d = OrderedDict()
    for n in ['coin_name', 'coin_shortcut', 'address_type', 'maxfee_kb', 'address_type_p2sh', 'address_type_p2wpkh', 'address_type_p2wsh', 'signed_message_header']:
        d[n] = c[n]
    print('    CoinType(')
    for k in d:
        print('        %s=%s,' % (k, repr(d[k])))
    print('    ),')
print(']\n')
