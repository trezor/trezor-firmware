#!/usr/bin/env python3

# This script generates coins.json files from the definitions in defs/
#
# - `./build_coins.py` generates a big file with everything
# - `./build_coins.py XXX` generates a file with coins supported by XXX
#      for example: `./build_coins.py webwallet` or `./build_coins.py trezor1`
# - `./build_coins.py XXX --defs` also adds protobuf definitions with TOIF icon
#
# generated file is coins.json in current directory,
# and coindefs.json if --def is enabled

import json
import glob
import re
import os
import sys

if '--defs' in sys.argv:
    from binascii import unhexlify
    from hashlib import sha256
    import ed25519
    from PIL import Image
    from trezorlib.protobuf import dump_message
    from coindef import CoinDef
    BUILD_DEFS = True
else:
    BUILD_DEFS = False


def check_type(val, types, nullable=False, empty=False, regex=None, choice=None):  # noqa:E501
    # check nullable
    if nullable and val is None:
        return True
    # check empty
    try:
        if not empty and len(val) == 0:
            return False
    except TypeError:
        pass
    # check regex
    if regex is not None:
        if types is not str:
            return False
        m = re.match(regex, val)
        if not m:
            return False
    # check choice
    if choice is not None:
        if val not in choice:
            return False
    # check type
    if isinstance(types, list):
        return True in [isinstance(val, t) for t in types]
    else:
        return isinstance(val, types)


def validate_coin(coin):
    assert check_type(coin['coin_name'], str, regex=r'^[A-Z]')
    assert check_type(coin['coin_shortcut'], str, regex=r'^[A-Zt][A-Z][A-Z]+$')
    assert check_type(coin['coin_label'], str, regex=r'^[A-Z]')
    assert check_type(coin['website'], str, regex=r'^http.*[^/]$')
    assert check_type(coin['github'], str, regex=r'^https://github.com/.*[^/]$')  # noqa:E501
    assert check_type(coin['maintainer'], str)
    assert check_type(coin['curve_name'], str, choice=['secp256k1', 'secp256k1_decred', 'secp256k1_groestl'])  # noqa:E501
    assert check_type(coin['address_type'], int)
    assert check_type(coin['address_type_p2sh'], int)
    assert coin['address_type'] != coin['address_type_p2sh']
    assert check_type(coin['maxfee_kb'], int)
    assert check_type(coin['minfee_kb'], int)
    assert coin['maxfee_kb'] >= coin['minfee_kb']
    assert check_type(coin['hash_genesis_block'], str, regex=r'^[0-9a-f]{64}$')
    assert check_type(coin['xprv_magic'], int)
    assert check_type(coin['xpub_magic'], int)
    assert check_type(coin['xpub_magic_segwit_p2sh'], int, nullable=True)
    assert check_type(coin['xpub_magic_segwit_native'], int, nullable=True)
    assert coin['xprv_magic'] != coin['xpub_magic']
    assert coin['xprv_magic'] != coin['xpub_magic_segwit_p2sh']
    assert coin['xprv_magic'] != coin['xpub_magic_segwit_native']
    assert coin['xpub_magic'] != coin['xpub_magic_segwit_p2sh']
    assert coin['xpub_magic'] != coin['xpub_magic_segwit_native']
    assert coin['xpub_magic_segwit_p2sh'] is None or coin['xpub_magic_segwit_native'] is None or coin['xpub_magic_segwit_p2sh'] != coin['xpub_magic_segwit_native']  # noqa:E501
    assert check_type(coin['slip44'], int)
    assert check_type(coin['segwit'], bool)
    assert check_type(coin['decred'], bool)
    assert check_type(coin['fork_id'], int, nullable=True)
    assert check_type(coin['force_bip143'], bool)
    assert check_type(coin['version_group_id'], int, nullable=True)
    assert check_type(coin['default_fee_b'], dict)
    assert check_type(coin['dust_limit'], int)
    assert check_type(coin['blocktime_seconds'], int)
    assert check_type(coin['signed_message_header'], str)
    assert check_type(coin['address_prefix'], str, regex=r'^.*:$')
    assert check_type(coin['min_address_length'], int)
    assert check_type(coin['max_address_length'], int)
    assert coin['max_address_length'] >= coin['min_address_length']
    assert check_type(coin['bech32_prefix'], str, nullable=True)
    assert check_type(coin['cashaddr_prefix'], str, nullable=True)
    assert check_type(coin['bitcore'], list, empty=True)
    for bc in coin['bitcore']:
        assert not bc.endswith('/')
    assert check_type(coin['blockbook'], list, empty=True)
    for bb in coin['blockbook']:
        assert not bb.endswith('/')


def validate_icon(icon):
    assert icon.size == (96, 96)
    assert icon.mode == 'RGBA'


class Writer:

    def __init__(self):
        self.buf = bytearray()

    def write(self, buf):
        self.buf.extend(buf)


def serialize(coin, icon):
    c = dict(coin)
    c['signed_message_header'] = c['signed_message_header'].encode()
    c['hash_genesis_block'] = unhexlify(c['hash_genesis_block'])
    c['icon'] = icon
    msg = CoinDef(**c)
    w = Writer()
    dump_message(w, msg)
    return bytes(w.buf)


def sign(data):
    h = sha256(data).digest()
    sign_key = ed25519.SigningKey(b'A' * 32)
    return sign_key.sign(h)


# conversion copied from trezor-core/tools/png2toi
# TODO: extract into common module in python-trezor
def convert_icon(icon):
    import struct
    import zlib
    w, h = 32, 32
    icon = icon.resize((w, h), Image.LANCZOS)
    # remove alpha channel, replace with black
    bg = Image.new('RGBA', icon.size, (0, 0, 0, 255))
    icon = Image.alpha_composite(bg, icon)
    # process pixels
    pix = icon.load()
    data = bytes()
    for j in range(h):
        for i in range(w):
            r, g, b, _ = pix[i, j]
            c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)
            data += struct.pack('>H', c)
    z = zlib.compressobj(level=9, wbits=10)
    zdata = z.compress(data) + z.flush()
    zdata = zdata[2:-4]  # strip header and checksum
    return zdata


def process_json(fn):
    print(os.path.basename(fn), end=' ... ')
    j = json.load(open(fn))
    validate_coin(j)
    if BUILD_DEFS:
        i = Image.open(fn.replace('.json', '.png'))
        validate_icon(i)
        ser = serialize(j, convert_icon(i))
        sig = sign(ser)
        definition = (sig + ser).hex()
        print('OK')
        return j, definition
    else:
        print('OK')
        return j, None


def process(for_device=None):
    scriptdir = os.path.dirname(os.path.realpath(__file__))

    support_json = json.load(open(scriptdir + '/../defs/support.json'))
    if for_device is not None:
        support_list = support_json[for_device].keys()
    else:
        support_list = None

    coins = {}
    defs = {}
    for fn in glob.glob(scriptdir + '/../defs/coins/*.json'):
        c, d = process_json(fn)
        n = c['coin_name']
        c['support'] = {}
        for s in support_json.keys():
            c['support'][s] = support_json[s][n] if n in support_json[s] else None  # noqa:E501
        if support_list is None or n in support_list:
            coins[n] = c
            defs[n] = d

    return (coins, defs)


if __name__ == '__main__':
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        for_device = sys.argv[1]
    else:
        for_device = None

    (coins, defs) = process(for_device)

    json.dump(coins, open('coins.json', 'w'), indent=4, sort_keys=True)
    if BUILD_DEFS:
        json.dump(defs, open('coindefs.json', 'w'), indent=4, sort_keys=True)

    # check for colliding address versions
    at_p2pkh = {}
    at_p2sh = {}
    slip44 = {}

    for n, c in coins.items():
        s = c['slip44']
        if s not in slip44:
            slip44[s] = []
        if not(n.endswith('Testnet') and s == 1):
            slip44[s].append(n)
        if c['cashaddr_prefix']:  # skip cashaddr currencies
            continue
        a1, a2 = c['address_type'], c['address_type_p2sh']
        if a1 not in at_p2pkh:
            at_p2pkh[a1] = []
        if a2 not in at_p2sh:
            at_p2sh[a2] = []
        at_p2pkh[a1].append(n)
        at_p2sh[a2].append(n)

    print()
    print('Colliding address_types for P2PKH:')
    for k, v in at_p2pkh.items():
        if len(v) >= 2:
            print('-', k, ':', ','.join(v))

    print()
    print('Colliding address_types for P2SH:')
    for k, v in at_p2sh.items():
        if len(v) >= 2:
            print('-', k, ':', ','.join(v))

    print()
    print('Colliding SLIP44 constants:')
    for k, v in slip44.items():
        if len(v) >= 2:
            print('-', k, ':', ','.join(v))
