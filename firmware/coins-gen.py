#!/usr/bin/env python3
import json

coins = json.load(open('../vendor/trezor-common/coins.json', 'r'))

fields = []

for c in coins:
    fields.append([
        'true' if c['coin_name'] is not None else 'false',
        '"%s"' % c['coin_name'] if c['coin_name'] is not None else 'NULL',

        'true' if c['coin_shortcut'] is not None else 'false',
        '" %s"' % c['coin_shortcut'] if c['coin_shortcut'] is not None else 'NULL',

        'true' if c['address_type'] is not None else 'false',
        '%d' % c['address_type'] if c['address_type'] is not None else '0',

        'true' if c['maxfee_kb'] is not None else 'false',
        '%d' % c['maxfee_kb'] if c['maxfee_kb'] is not None else '0',

        'true' if c['address_type_p2sh'] is not None else 'false',
        '%d' % c['address_type_p2sh'] if c['address_type_p2sh'] is not None else '0',

        'true' if c['signed_message_header'] is not None else 'false',
        '"\\x%02x" "%s"' % (len(c['signed_message_header']), c['signed_message_header'].replace('\n', '\\n')) if c['signed_message_header'] is not None else 'NULL',

        'true' if c['xpub_magic'] is not None else 'false',
        '0x%s' % c['xpub_magic'] if c['xpub_magic'] is not None else '00000000',

        'true' if c['xprv_magic'] is not None else 'false',
        '0x%s' % c['xprv_magic'] if c['xprv_magic'] is not None else '00000000',

        'true' if c['segwit'] is not None else 'false',
        'true' if c['segwit'] else 'false',

        'true' if c['forkid'] is not None else 'false',
        '%d' % c['forkid'] if c['forkid'] else '0'
    ])

for j in range(len(fields[0])):
    l = max([len(x[j]) for x in fields]) + 1
    for i in range(len(fields)):
        if fields[i][j][0] in '0123456789':
            fields[i][j] = (fields[i][j] + ',').rjust(l)
        else:
            fields[i][j] = (fields[i][j] + ',').ljust(l)

for row in fields:
    print('\t{' + ' '.join(row) + ' },')
