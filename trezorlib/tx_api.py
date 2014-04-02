import binascii
import urllib2
import json
try:
    from filecache import filecache, MONTH
except:
    def filecache(x):
        def _inner(y):
            return y
        return _inner
    MONTH = None

import types_pb2 as proto_types

def op_push(i):
    if i<0x4c:
        return chr(i)
    elif i<0xff:
        return '\x4c' + chr(i)
    elif i<0xffff:
        return '\x4d' + struct.pack("<H", i)
    else:
        return '\x4e' + struct.pack("<I", i)

def opcode_serialize(opcode):
    # TODO: this function supports just small subset of script for now (enough for most transactions)
    if opcode == 'OP_DUP':
        return '\x76'
    if opcode == 'OP_HASH160':
        return '\xa9'
    if opcode == 'OP_EQUAL':
        return '\x87'
    if opcode == 'OP_EQUALVERIFY':
        return '\x88'
    if opcode == 'OP_CHECKSIG':
        return '\xac'
    # it's probably hex data
    try:
        x = binascii.unhexlify(opcode)
        return op_push(len(x)) + x
    except:
        raise Exception('Unknown script opcode: %s' % opcode)

def bitcore_tx(url):
    f = urllib2.urlopen(url)
    data = json.load(f)

    t = proto_types.TransactionType()
    t.version = data['version']
    t.lock_time = data['locktime']

    for vin in data['vin']:
        i = t.inputs.add()
        i.prev_hash = binascii.unhexlify(vin['txid'])
        i.prev_index = vin['vout']
        asm = vin['scriptSig']['asm'].split(' ')
        asm = [ opcode_serialize(x) for x in asm ]
        i.script_sig = ''.join(asm)
        i.sequence = vin['sequence']

    for vout in data['vout']:
        o = t.outputs.add()
        o.amount = int(vout['value'] * 100000000)
        asm = vout['scriptPubKey']['asm'].split(' ')
        asm = [ opcode_serialize(x) for x in asm ]
        o.script_pubkey = ''.join(asm)

    return t

class TXAPIBitcoin(object):

    @filecache(MONTH)
    def get_tx(self, txhash):
        url = 'http://live.bitcore.io/api/tx/%s' % txhash
        return bitcore_tx(url)

class TXAPITestnet(object):

    @filecache(MONTH)
    def get_tx(self, txhash):
        url = 'http://test.bitcore.io/api/tx/%s' % txhash
        return bitcore_tx(url)
