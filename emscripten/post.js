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
var _hdnode_public_ckd = Module['_hdnode_public_ckd'];
var _ecdsa_get_address = Module['_ecdsa_get_address'];
var Pointer_stringify = Module['Pointer_stringify'];

// HDNode struct global
var HDNODE_SIZE = 4 + 4 + 4 + 32 + 32 + 33;
var _hdnode = _malloc(HDNODE_SIZE);

// address string global
var ADDRESS_SIZE = 40; // maximum size
var _address = _malloc(ADDRESS_SIZE);

/*
 * public library interface
 */

/**
 * @param {HDNode} node  HDNode struct, see the definition above
 * @return {Uint8Array}
 */
function serializeNode(node) {
    var b = new ArrayBuffer(HDNODE_SIZE);

    var u32 = new Uint32Array(b, 0, 12);
    u32[0] = node['depth'];
    u32[1] = node['fingerprint'];
    u32[2] = node['child_num'];

    var u8 = new Uint8Array(b, 0, HDNODE_SIZE);
    u8.set(node['chain_code'], 12);
    u8.set(node['public_key'], 12 + 32 + 32);

    return u8;
}

/**
 * @param {Uint8Array} sn   serialized node, see `serializeNode`
 * @param {Number} index    BIP32 index of the address
 * @param {Number} version  address version byte
 * @return {String}
 */
function deriveAddress(sn, index, version) {
    HEAPU8.set(sn, _hdnode);
    _hdnode_public_ckd(_hdnode, index);
    _ecdsa_get_address(_hdnode + 12 + 32 + 32, version, _address, ADDRESS_SIZE);
    return Pointer_stringify(_address);
}

/**
 * @param {HDNode} node        HDNode struct, see the definition above
 * @param {Number} firstIndex  index of the first address
 * @param {Number} lastIndex   index of the last address
 * @param {Number} version     address version byte
 * @return {Array<String>}
 */
function deriveAddressRange(node, firstIndex, lastIndex, version) {
    var addresses = [];
    var sn = serializeNode(node);
    var i;
    for (i = firstIndex; i <= lastIndex; i++) {
        addresses.push(deriveAddress(sn, i, version));
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
            data['version']
        );
        postMessage({
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
    this['onmessage'] = processMessage;
}
