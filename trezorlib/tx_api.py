import binascii
import urllib2
import json
from decimal import Decimal
try:
    raise Exception() # remove this line to enable caching
    from filecache import filecache, DAY
except:
    def filecache(x):
        def _inner(y):
            return y
        return _inner
    DAY = None

import types_pb2 as proto_types

def op_push_data(data):
    l = len(data)
    if l < 0x4C:
        return chr(l) + data
    elif i < 0xFF:
        return '\x4C' + chr(l) + data
    elif i < 0xFFFF:
        return '\x4D' + struct.pack("<H", i) + data
    else:
        return '\x4E' + struct.pack("<I", i) + data

def opcode_serialize(opcode):
    mapping = {
        'OP_TRUE'                : '\x51',
        'OP_RETURN'              : '\x6A',
        'OP_DUP'                 : '\x76',
        'OP_EQUAL'               : '\x87',
        'OP_EQUALVERIFY'         : '\x88',
        'OP_RIPEMD160'           : '\xA6',
        'OP_SHA1'                : '\xA7',
        'OP_SHA256'              : '\xA8',
        'OP_HASH160'             : '\xA9',
        'OP_HASH256'             : '\xAA',
        'OP_CHECKSIG'            : '\xAC',
        'OP_CHECKSIGVERIFY'      : '\xAD',
        'OP_CHECKMULTISIG'       : '\xAE',
        'OP_CHECKMULTISIGVERIFY' : '\xAF',
    }
    # check if it is known opcode
    if mapping.has_key(opcode):
        return mapping[opcode]
    # it's probably hex data
    try:
        x = binascii.unhexlify(opcode)
        return op_push_data(x)
    except:
        raise Exception('Unknown script opcode: %s' % opcode)

def insight_tx(url):
    try:
        f = urllib2.urlopen(url)
    except:
        raise Exception('URL error: %s' % url)
    data = json.load(f)

    t = proto_types.TransactionType()
    t.version = data['version']
    t.lock_time = data['locktime']

    for vin in data['vin']:
        i = t.inputs.add()
        if 'coinbase' in vin.keys():
            i.prev_hash = "\0"*32
            i.prev_index = 0xffffffff # signed int -1
            i.script_sig = binascii.unhexlify(vin['coinbase'])
            i.sequence = vin['sequence']

        else:
            i.prev_hash = binascii.unhexlify(vin['txid'])
            i.prev_index = vin['vout']
            asm = vin['scriptSig']['asm'].split(' ')
            asm = [ opcode_serialize(x) for x in asm ]
            i.script_sig = ''.join(asm)
            i.sequence = vin['sequence']

    for vout in data['vout']:
        o = t.bin_outputs.add()
        o.amount = int(Decimal(vout['value']) * 100000000)
        asm = vout['scriptPubKey']['asm'].split(' ')
        asm = [ opcode_serialize(x) for x in asm ]
        o.script_pubkey = ''.join(asm)

    return t

class TXAPIBitcoin(object):

    @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://insight.bitpay.com/api/tx/%s' % txhash
        return insight_tx(url)

class TXAPITestnet(object):

    @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://test-insight.bitpay.com/api/tx/%s' % txhash
        return insight_tx(url)
