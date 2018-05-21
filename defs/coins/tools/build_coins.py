#!/usr/bin/env python3

import json
import glob
import re
from hashlib import sha256
from binascii import unhexlify

import ed25519
from PIL import Image

from trezorlib.protobuf import dump_message
from coindef import CoinDef


def check_type(val, types, nullable=False, empty=False, regex=None, choice=None):
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
    assert check_type(coin['github'], str, regex=r'^https://github.com/.*[^/]$')
    assert check_type(coin['maintainer'], str)
    assert check_type(coin['curve_name'], str, choice=['secp256k1', 'secp256k1_decred', 'secp256k1_groestl'])
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
    assert coin['xpub_magic_segwit_p2sh'] is None or coin['xpub_magic_segwit_native'] is None or coin['xpub_magic_segwit_p2sh'] != coin['xpub_magic_segwit_native']
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
    print(fn, end=' ... ')
    j = json.load(open(fn))
    i = Image.open(fn.replace('.json', '.png'))
    validate_coin(j)
    validate_icon(i)
    ser = serialize(j, convert_icon(i))
    sig = sign(ser)
    definition = (sig + ser).hex()
    print('OK')
    return j, definition


coins = {}
defs = {}
for fn in glob.glob('../*.json'):
    c, d = process_json(fn)
    n = c['coin_name']
    coins[n] = c
    defs[n] = d


json.dump(coins, open('../../coins.json', 'w'), indent=4, sort_keys=True)
json.dump(defs, open('../../coindefs.json', 'w'), indent=4, sort_keys=True)
