'''
    Blockchain API implementing Blockchain.info interface
'''
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

class BlockchainApi(object):
    def _raw_tx(self, txhash):
        # Download tx data from blockchain.info
        url = 'http://blockchain.info/rawtx/%s?scripts=true' % txhash
        print "Downloading", url
        f = urllib2.urlopen(url)
        return json.load(f)

    def submit(self, tx):
        raise Exception("Not implemented yet")

    @filecache(MONTH)
    def get_tx(self, txhash):
        # Build protobuf transaction structure from blockchain.info
        d = self._raw_tx(txhash)
        t = proto_types.TransactionType()

        for inp in d['inputs']:
            di = self._raw_tx(inp['prev_out']['tx_index'])
            i = t.inputs.add()
            i.prev_hash = binascii.unhexlify(di['hash'])
            i.prev_index = inp['prev_out']['n']
            i.script_sig = binascii.unhexlify(inp['script'])

        for output in d['out']:
            o = t.outputs.add()
            o.amount = output['value']
            o.script_pubkey = binascii.unhexlify(output['script'])

        t.version = 1
        t.lock_time = 0
        return t

if __name__ == '__main__':
    api = BlockchainApi()
    print api.get_tx('b9f382b8dfc34accc05491712a1ad8f7f075a02056dc4821d1f60702fb3fdb2f')
