var crypto = require('./trezor-crypto');

/* typedef struct {
   uint32_t depth;
   uint32_t fingerprint;
   uint32_t child_num;
   uint8_t chain_code[32];
   uint8_t private_key[32];
   uint8_t public_key[33];
   } HDNode;
*/

var HDNODE_SIZE = 4 + 4 + 4 + 32 + 32 + 33;
var hdnode = crypto._malloc(HDNODE_SIZE);

var ADDRESS_SIZE = 40; // maximum size
var address = crypto._malloc(ADDRESS_SIZE);

function prepareNode(n) {
    var b = new ArrayBuffer(HDNODE_SIZE);
    var u8 = new Uint8Array(b, 0, HDNODE_SIZE);
    var u32 = new Uint32Array(b, 0, 12);

    u32[0] = n.depth;
    u32[1] = n.parentFingerprint;
    u32[2] = n.index;
    u8.set(n.chainCode, 12);
    u8.set(n.pubKey.toBuffer(), 12 + 32 + 32);

    return u8;
}

function deriveAddress(pn, i, version) {
    crypto.HEAPU8.set(pn, hdnode);
    crypto._hdnode_public_ckd(hdnode, i);
    crypto._ecdsa_get_address(hdnode + 12 + 32 + 32, version, address, ADDRESS_SIZE);
    return crypto.Pointer_stringify(address);
}

// benching code

var bitcoin = require('bitcoinjs-lib');

var node = bitcoin.HDNode.fromBase58(
    'xpub6AHA9hZDN11k2ijHMeS5QqHx2KP9aMBRhTDqANMnwVtdyw2TDYRm' +
        'F8PjpvwUFcL1Et8Hj59S3gTSMcUQ5gAqTz3Wd8EsMTmF3DChhqPQBnU'
).derive(0);

timeBitcoinjs(node);
timeTrezorCrypto(node);

function timeBitcoinjs(n) {
    console.time('bitcoinjs')
    for (var i = 0; i < 1000; i++) {
        n.derive(i).getAddress()
    }
    console.timeEnd('bitcoinjs')
}

function timeTrezorCrypto(n) {
    var nP = prepareNode(n);
    console.time('trezor-crypto')
    for (var i = 0; i < 1000; i++) {
        deriveAddress(nP, i, 0);
    }
    console.timeEnd('trezor-crypto')
}
