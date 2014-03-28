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

class TXAPIBlockchain(object):
    def _raw_tx(self, txhash):
        # Download tx data from blockchain.info
        url = 'http://blockchain.info/rawtx/%s?scripts=true' % txhash
        print "Downloading", url
        f = urllib2.urlopen(url)
        return json.load(f)

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

class TXAPITestnetFake(object):
    def get_tx(self, txhash):
        if txhash != '6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54':
            raise Exception("Unexpected hash")

        t = proto_types.TransactionType()

        i = t.inputs.add()
        i.prev_hash = binascii.unhexlify('ee336e79153d51f4f3e45278f1f77ab29fd5bb135dce467282e2aff22cb9c570')
        i.prev_index = 1
        i.script_sig = binascii.unhexlify('483045022066c418874dbe5628296700382d727ce1734928796068c26271472df09dccf1a20221009dec59d19f9d73db381fcd35c0fff757ad73e54ef59157b0d7c57e6739a092f00121033fef08c603943dc7d25f4ce65771762143b1cd8678343d660a1a76b9d1d3ced7')

        i = t.inputs.add()
        i.prev_hash = binascii.unhexlify('2fe4d8af2b44faccc10dd5a6578c923491d2d21269a1dfe8c83f492a30fb8f9f')
        i.prev_index = 1
        i.script_sig = binascii.unhexlify('47304402206fbb8e14be706b8557a2280d2a2a75c0a65c4f7936d90d510f0971c93f41f74402201b79c8c4e4ac4c944913611633c230193558296e70a36269b7fc3a80efa27d120121030cb5be79bdc36a4ff4443dbac43068cc43d638ea06ff2fa1b8dab389e39aefc7')

        o = t.outputs.add()
        o.amount = 403850989
        o.script_pubkey = binascii.unhexlify('76a914f5a05c2664b40d3116b1c5086c9ba38ed15b742e88ac')

        o = t.outputs.add()
        o.amount = 1000000000
        o.script_pubkey = binascii.unhexlify('76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac')

        t.version = 1
        t.lock_time = 0
        return t

if __name__ == '__main__':
    api = TXAPIBlockchain()
    print api.get_tx('b9f382b8dfc34accc05491712a1ad8f7f075a02056dc4821d1f60702fb3fdb2f')
