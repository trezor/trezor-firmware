var crypto = require('./trezor-crypto');
var bitcoin = require('bitcoinjs-lib');

var XPUB =
    'xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx';
var node = bitcoin.HDNode.fromBase58(XPUB).derive(0);

var nodeStruct = {
    depth: node.depth,
    child_num: node.index,
    fingerprint: node.parentFingerprint,
    chain_code: node.chainCode,
    public_key: node.keyPair.getPublicKeyBuffer()
};

var addresses = crypto.deriveAddressRange(nodeStruct, 0, 999, 5, true);

var fs = require('fs');
var loaded = fs.readFileSync('test-addresses-segwit-p2sh.txt').toString().split("\n");

for (var i = 0; i < 1000; i++) {
  if (loaded[i] !== addresses[i]) {
    console.log("bad address", i);
    process.exit(1)
  }
}

console.log("Testing address ended correctly");
process.exit(0)

