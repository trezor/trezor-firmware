#!/usr/bin/env python3
import json


def format_str(value):
    return '"' + value + '"'


def format_primitive(value):
    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        return format_str(value)
    elif isinstance(value, list):
        return value
    else:
        raise TypeError


fields = [
    'name',
    'ticker',
    'namespace',
    'mosaic',
    'divisibility',
    'levy',
    'fee',
    'levy_namespace',
    'levy_mosaic',
    'networks',
]

mosaics = json.load(open('../../vendor/trezor-common/defs/nem/nem_mosaics.json', 'r'))

print('# generated using gen_nem_mosaics.py from trezor-common nem_mosaics.json - do not edit directly!')
print('')
print('mosaics = [')
for m in mosaics:
    print('    {')
    for name in fields:
        if name in m:
            print('        %s: %s,' % (format_str(name), format_primitive(m[name])))
        # else:
        #     print('        %s: None,' % format_str(name))
    print('    },')
print(']')
