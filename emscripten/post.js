/*
 typedef struct {
 uint32_t depth;
 uint32_t fingerprint;
 uint32_t child_num;
 uint8_t chain_code[32];
 uint8_t private_key[32];
 uint8_t public_key[33];
 } HDNode;
 */

var HEAPU8 = Module['HEAPU8'];
var _malloc = Module['_malloc'];
var _hdnode_public_ckd_address_optimized = Module['_hdnode_public_ckd_address_optimized'];
var _ecdsa_read_pubkey = Module['_ecdsa_read_pubkey'];
var Pointer_stringify = Module['Pointer_stringify'];

// HDNode structs global
var PUBPOINT_SIZE = 2 * 9 * 4; // (2 * bignum256 (= 9 * uint32_t))
var _pubpoint = _malloc(PUBPOINT_SIZE);
var PUBKEY_SIZE = 33;
var _pubkey = _malloc(PUBKEY_SIZE);
var CHAINCODE_SIZE = 32;
var _chaincode = _malloc(CHAINCODE_SIZE);

// address string global
var ADDRESS_SIZE = 60; // maximum size
var _address = _malloc(ADDRESS_SIZE);

/*
 * public library interface
 */

/**
 * @param {HDNode} node  HDNode struct, see the definition above
 */
function serializeNode(node) {
    var u8_pubkey = new Uint8Array(33);
    u8_pubkey.set(node['public_key'], 0);
    HEAPU8.set(u8_pubkey, _pubkey);

    var u8_chaincode = new Uint8Array(32);
    u8_chaincode.set(node['chain_code'], 0);
    HEAPU8.set(u8_chaincode, _chaincode);

    _ecdsa_read_pubkey(0, _pubkey, _pubpoint);
}

/**
 * @param {Number} index    BIP32 index of the address
 * @param {Number} version  address version byte
 * @return {String}
 */
function deriveAddress(index, version, segwit) {
    _hdnode_public_ckd_address_optimized(_pubpoint, _chaincode, index, version, _address, ADDRESS_SIZE, segwit);
    return Pointer_stringify(_address);
}

/**
 * @param {HDNode} node        HDNode struct, see the definition above
 * @param {Number} firstIndex  index of the first address
 * @param {Number} lastIndex   index of the last address
 * @param {Number} version     address version byte
 * @return {Array<String>}
 */
function deriveAddressRange(node, firstIndex, lastIndex, version, segwit) {
    var addresses = [];
    serializeNode(node);
    var i;
    for (i = firstIndex; i <= lastIndex; i++) {
        addresses.push(deriveAddress(i, version, segwit));
    }
    return addresses;
}

if (typeof module !== 'undefined') {
    module['exports'] = {
        'serializeNode': serializeNode,
        'deriveAddress': deriveAddress,
        'deriveAddressRange': deriveAddressRange
    };
}

/*
 * Web worker processing
 */

function processMessage(event) {
    var data = event['data'];
    var type = data['type'];

    switch (type) {
    case 'deriveAddressRange':
        var addresses = deriveAddressRange(
            data['node'],
            data['firstIndex'],
            data['lastIndex'],
            data['version'],
            !!data['segwit']
        );
        self.postMessage({
            'addresses': addresses,
            'firstIndex': data['firstIndex'],
            'lastIndex': data['lastIndex']
        });
        break;

    default:
        throw new Error('Unknown message type: ' + type);
    }
}

if (ENVIRONMENT_IS_WORKER) {
    self.onmessage = processMessage;
}
