var crypto = require('./trezor-crypto');
var bitcoin = require('bitcoinjs-lib');

var XPUB =
    'xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy';
var node = bitcoin.HDNode.fromBase58(XPUB).derive(0);

var nodeStruct = {
    depth: node.depth,
    child_num: node.index,
    fingerprint: node.parentFingerprint,
    chain_code: node.chainCode,
    public_key: node.keyPair.getPublicKeyBuffer()
};

var addresses = crypto.deriveAddressRange(nodeStruct, 0, 999, 0, false);

// for segwit:
// var addresses = crypto.deriveAddressRange(nodeStruct, 0, 999, 5, true);

var fs = require('fs');
var loaded = fs.readFileSync('test-addresses.txt').toString().split("\n");

for (var i = 0; i < 1000; i++) {
  if (loaded[i] !== addresses[i]) {
    console.log("bad address", i);
    process.exit(1)
  }
}

console.log("Testing address ended correctly");
process.exit(0)

