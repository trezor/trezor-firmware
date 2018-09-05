/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "py/objstr.h"

#include "embed/extmod/trezorobj.h"

#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "memzero.h"
#include "nem.h"

/// class HDNode:
///     '''
///     BIP0032 HD node structure.
///     '''
typedef struct _mp_obj_HDNode_t {
    mp_obj_base_t base;
    uint32_t fingerprint;
    HDNode hdnode;
} mp_obj_HDNode_t;

STATIC const mp_obj_type_t mod_trezorcrypto_HDNode_type;

#define XPUB_MAXLEN 128
#define ADDRESS_MAXLEN 36

/// def __init__(self,
///              depth: int,
///              fingerprint: int,
///              child_num: int,
///              chain_code: bytes,
///              private_key: bytes = None,
///              public_key: bytes = None,
///              curve_name: str = None) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_depth,        MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_fingerprint,  MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_child_num,    MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_chain_code,   MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_private_key,                    MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_public_key,                     MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_curve_name,                     MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    mp_buffer_info_t chain_code;
    mp_buffer_info_t private_key;
    mp_buffer_info_t public_key;
    mp_buffer_info_t curve_name;
    const uint32_t depth       = trezor_obj_get_uint(vals[0].u_obj);
    const uint32_t fingerprint = trezor_obj_get_uint(vals[1].u_obj);
    const uint32_t child_num   = trezor_obj_get_uint(vals[2].u_obj);
    mp_get_buffer_raise(vals[3].u_obj, &chain_code, MP_BUFFER_READ);
    mp_get_buffer_raise(vals[4].u_obj, &private_key, MP_BUFFER_READ);
    mp_get_buffer_raise(vals[5].u_obj, &public_key, MP_BUFFER_READ);
    mp_get_buffer_raise(vals[6].u_obj, &curve_name, MP_BUFFER_READ);

    if (32 != chain_code.len) {
        mp_raise_ValueError("chain_code is invalid");
    }
    if (0 == public_key.len && 0 == private_key.len) {
        mp_raise_ValueError("either public_key or private_key is required");
    }
    if (0 != private_key.len && 32 != private_key.len) {
        mp_raise_ValueError("private_key is invalid");
    }
    if (0 != public_key.len && 33 != public_key.len) {
        mp_raise_ValueError("public_key is invalid");
    }

    const curve_info *curve = NULL;
    if (0 == curve_name.len) {
        curve = get_curve_by_name(SECP256K1_NAME);
    } else {
        curve = get_curve_by_name(curve_name.buf);
    }
    if (NULL == curve) {
        mp_raise_ValueError("curve_name is invalid");
    }

    mp_obj_HDNode_t *o = m_new_obj(mp_obj_HDNode_t);
    o->base.type = type;

    o->fingerprint = fingerprint;
    o->hdnode.depth = depth;
    o->hdnode.child_num = child_num;
    if (32 == chain_code.len) {
        memcpy(o->hdnode.chain_code, chain_code.buf, 32);
    } else {
        memzero(o->hdnode.chain_code, 32);
    }
    if (32 == private_key.len) {
        memcpy(o->hdnode.private_key, private_key.buf, 32);
    } else {
        memzero(o->hdnode.private_key, 32);
    }
    if (33 == public_key.len) {
        memcpy(o->hdnode.public_key, public_key.buf, 33);
    } else {
        memzero(o->hdnode.public_key, 33);
    }
    o->hdnode.curve = curve;

    return MP_OBJ_FROM_PTR(o);
}

/// def derive(self, index: int, public: bool=False) -> None:
///     '''
///     Derive a BIP0032 child node in place.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_derive(size_t n_args, const mp_obj_t *args) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(args[0]);
    uint32_t i = trezor_obj_get_uint(args[1]);
    uint32_t fp = hdnode_fingerprint(&o->hdnode);
    bool public = n_args > 2 && args[2] == mp_const_true;

    int res;
    if (public) {
        res = hdnode_public_ckd(&o->hdnode, i);
    } else {
        if (0 == memcmp(o->hdnode.private_key, "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32)) {
            memzero(&o->hdnode, sizeof(o->hdnode));
            mp_raise_ValueError("Failed to derive, private key not set");
        }
        res = hdnode_private_ckd(&o->hdnode, i);
    }
    if (!res) {
        memzero(&o->hdnode, sizeof(o->hdnode));
        mp_raise_ValueError("Failed to derive");
    }
    o->fingerprint = fp;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_HDNode_derive_obj, 2, 3, mod_trezorcrypto_HDNode_derive);

/// def derive_cardano(self, index: int) -> None:
///     '''
///     Derive a BIP0032 child node in place using Cardano algorithm.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_derive_cardano(mp_obj_t self, mp_obj_t index) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    uint32_t i = mp_obj_get_int_truncated(index);
    uint32_t fp = hdnode_fingerprint(&o->hdnode);
    int res;
    // same as in derive
    if (0 == memcmp(o->hdnode.private_key, "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32)) {
        memzero(&o->hdnode, sizeof(o->hdnode));
        mp_raise_ValueError("Failed to derive, private key not set");
    }
    // special for cardano
    res = hdnode_private_ckd_cardano(&o->hdnode, i);
    if (!res) {
        memzero(&o->hdnode, sizeof(o->hdnode));
        mp_raise_ValueError("Failed to derive");
    }
    o->fingerprint = fp;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_derive_cardano_obj, mod_trezorcrypto_HDNode_derive_cardano);

/// def derive_path(self, path: List[int]) -> None:
///     '''
///     Go through a list of indexes and iteratively derive a child node in place.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_derive_path(mp_obj_t self, mp_obj_t path) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

    // get path objects and length
    size_t plen;
    mp_obj_t *pitems;
    mp_obj_get_array(path, &plen, &pitems);
    if (plen > 32) {
        mp_raise_ValueError("Path cannot be longer than 32 indexes");
    }

    // convert path to int array
    uint32_t pi;
    uint32_t pints[plen];
    for (pi = 0; pi < plen; pi++) {
        pints[pi] = trezor_obj_get_uint(pitems[pi]);
    }

    if (!hdnode_private_ckd_cached(&o->hdnode, pints, plen, &o->fingerprint)) {
        // derivation failed, reset the state and raise
        o->fingerprint = 0;
        memzero(&o->hdnode, sizeof(o->hdnode));
        mp_raise_ValueError("Failed to derive path");
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_derive_path_obj, mod_trezorcrypto_HDNode_derive_path);

STATIC mp_obj_t serialize_public_private(mp_obj_t self, bool use_public, uint32_t version) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    char xpub[XPUB_MAXLEN] = {0};
    int written;
    if (use_public) {
        hdnode_fill_public_key(&o->hdnode);
        written = hdnode_serialize_public(&o->hdnode, o->fingerprint, version, xpub, XPUB_MAXLEN);
    } else {
        written = hdnode_serialize_private(&o->hdnode, o->fingerprint, version, xpub, XPUB_MAXLEN);
    }
    if (written <= 0) {
        mp_raise_ValueError("Failed to serialize");
    }
    return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)xpub, written - 1);  // written includes 0 at the end
}

/// def serialize_public(self, version: int) -> str:
///     '''
///     Serialize the public info from HD node to base58 string.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_serialize_public(mp_obj_t self, mp_obj_t version) {
    uint32_t ver = trezor_obj_get_uint(version);
    return serialize_public_private(self, true, ver);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_serialize_public_obj, mod_trezorcrypto_HDNode_serialize_public);

/// def serialize_private(self, version: int) -> str:
///     '''
///     Serialize the private info HD node to base58 string.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_serialize_private(mp_obj_t self, mp_obj_t version) {
    uint32_t ver = trezor_obj_get_uint(version);
    return serialize_public_private(self, false, ver);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_serialize_private_obj, mod_trezorcrypto_HDNode_serialize_private);

/// def clone(self) -> HDNode:
///     '''
///     Returns a copy of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_clone(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    mp_obj_HDNode_t *copy = m_new_obj(mp_obj_HDNode_t);
    copy->base.type = &mod_trezorcrypto_HDNode_type;
    copy->hdnode = o->hdnode;
    copy->fingerprint = o->fingerprint;
    return MP_OBJ_FROM_PTR(copy);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_clone_obj, mod_trezorcrypto_HDNode_clone);

/// def depth(self) -> int:
///     '''
///     Returns a depth of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_depth(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_int_from_uint(o->hdnode.depth);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_depth_obj, mod_trezorcrypto_HDNode_depth);

/// def fingerprint(self) -> int:
///     '''
///     Returns a fingerprint of the HD node (hash of the parent public key).
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_fingerprint(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_int_from_uint(o->fingerprint);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_fingerprint_obj, mod_trezorcrypto_HDNode_fingerprint);

/// def child_num(self) -> int:
///     '''
///     Returns a child index of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_child_num(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_int_from_uint(o->hdnode.child_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_child_num_obj, mod_trezorcrypto_HDNode_child_num);

/// def chain_code(self) -> bytes:
///     '''
///     Returns a chain code of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_chain_code(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_bytes(o->hdnode.chain_code, sizeof(o->hdnode.chain_code));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_chain_code_obj, mod_trezorcrypto_HDNode_chain_code);

/// def private_key(self) -> bytes:
///     '''
///     Returns a private key of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_private_key(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_bytes(o->hdnode.private_key, sizeof(o->hdnode.private_key));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_private_key_obj, mod_trezorcrypto_HDNode_private_key);

/// def private_key_ext(self) -> bytes:
///     '''
///     Returns a private key extension of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_private_key_ext(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    return mp_obj_new_bytes(o->hdnode.private_key_extension, sizeof(o->hdnode.private_key_extension));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_private_key_ext_obj, mod_trezorcrypto_HDNode_private_key_ext);

/// def public_key(self) -> bytes:
///     '''
///     Returns a public key of the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_public_key(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
    hdnode_fill_public_key(&o->hdnode);
    return mp_obj_new_bytes(o->hdnode.public_key, sizeof(o->hdnode.public_key));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_public_key_obj, mod_trezorcrypto_HDNode_public_key);

/// def address(self, version: int) -> str:
///     '''
///     Compute a base58-encoded address string from the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_address(mp_obj_t self, mp_obj_t version) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

    uint32_t v = trezor_obj_get_uint(version);

    char address[ADDRESS_MAXLEN] = {0};
    hdnode_get_address(&o->hdnode, v, address, ADDRESS_MAXLEN);
    return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)address, strlen(address));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_address_obj, mod_trezorcrypto_HDNode_address);

/// def nem_address(self, network: int) -> str:
///     '''
///     Compute a NEM address string from the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_nem_address(mp_obj_t self, mp_obj_t network) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

    uint8_t n = trezor_obj_get_uint8(network);

    char address[NEM_ADDRESS_SIZE + 1] = {0}; // + 1 for the 0 byte
    if (!hdnode_get_nem_address(&o->hdnode, n, address)) {
        mp_raise_ValueError("Failed to compute a NEM address");
    }
    return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)address, strlen(address));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_nem_address_obj, mod_trezorcrypto_HDNode_nem_address);

/// def nem_encrypt(self, transfer_public_key: bytes, iv: bytes, salt: bytes, payload: bytes) -> bytes:
///     '''
///     Encrypts payload using the transfer's public key
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_nem_encrypt(size_t n_args, const mp_obj_t *args) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(args[0]);

    mp_buffer_info_t transfer_pk;
    mp_get_buffer_raise(args[1], &transfer_pk, MP_BUFFER_READ);
    if (transfer_pk.len != 32) {
        mp_raise_ValueError("transfer_public_key has invalid length");
    }

    mp_buffer_info_t iv;
    mp_get_buffer_raise(args[2], &iv, MP_BUFFER_READ);
    if (iv.len != 16) {
        mp_raise_ValueError("iv has invalid length");
    }
    mp_buffer_info_t salt;
    mp_get_buffer_raise(args[3], &salt, MP_BUFFER_READ);
    if (salt.len != NEM_SALT_SIZE) {
        mp_raise_ValueError("salt has invalid length");
    }
    mp_buffer_info_t payload;
    mp_get_buffer_raise(args[4], &payload, MP_BUFFER_READ);
    if (payload.len == 0) {
        mp_raise_ValueError("payload is empty");
    }

    vstr_t vstr;
    vstr_init_len(&vstr, NEM_ENCRYPTED_SIZE(payload.len));
    if (!hdnode_nem_encrypt(&o->hdnode, *(const ed25519_public_key *)transfer_pk.buf, iv.buf, salt.buf, payload.buf, payload.len, (uint8_t *)vstr.buf)) {
        mp_raise_ValueError("HDNode nem encrypt failed");
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_HDNode_nem_encrypt_obj, 5, 5, mod_trezorcrypto_HDNode_nem_encrypt);

/// def ethereum_pubkeyhash(self) -> bytes:
///     '''
///     Compute an Ethereum pubkeyhash (aka address) from the HD node.
///     '''
STATIC mp_obj_t mod_trezorcrypto_HDNode_ethereum_pubkeyhash(mp_obj_t self) {
    mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

    uint8_t pkh[20];
    hdnode_get_ethereum_pubkeyhash(&o->hdnode, pkh);
    return mp_obj_new_bytes(pkh, sizeof(pkh));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_ethereum_pubkeyhash_obj, mod_trezorcrypto_HDNode_ethereum_pubkeyhash);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_HDNode_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_derive), MP_ROM_PTR(&mod_trezorcrypto_HDNode_derive_obj) },
    { MP_ROM_QSTR(MP_QSTR_derive_cardano), MP_ROM_PTR(&mod_trezorcrypto_HDNode_derive_cardano_obj) },
    { MP_ROM_QSTR(MP_QSTR_derive_path), MP_ROM_PTR(&mod_trezorcrypto_HDNode_derive_path_obj) },
    { MP_ROM_QSTR(MP_QSTR_serialize_private), MP_ROM_PTR(&mod_trezorcrypto_HDNode_serialize_private_obj) },
    { MP_ROM_QSTR(MP_QSTR_serialize_public), MP_ROM_PTR(&mod_trezorcrypto_HDNode_serialize_public_obj) },

    { MP_ROM_QSTR(MP_QSTR_clone), MP_ROM_PTR(&mod_trezorcrypto_HDNode_clone_obj) },
    { MP_ROM_QSTR(MP_QSTR_depth), MP_ROM_PTR(&mod_trezorcrypto_HDNode_depth_obj) },
    { MP_ROM_QSTR(MP_QSTR_fingerprint), MP_ROM_PTR(&mod_trezorcrypto_HDNode_fingerprint_obj) },
    { MP_ROM_QSTR(MP_QSTR_child_num), MP_ROM_PTR(&mod_trezorcrypto_HDNode_child_num_obj) },
    { MP_ROM_QSTR(MP_QSTR_chain_code), MP_ROM_PTR(&mod_trezorcrypto_HDNode_chain_code_obj) },
    { MP_ROM_QSTR(MP_QSTR_private_key), MP_ROM_PTR(&mod_trezorcrypto_HDNode_private_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_private_key_ext), MP_ROM_PTR(&mod_trezorcrypto_HDNode_private_key_ext_obj) },
    { MP_ROM_QSTR(MP_QSTR_public_key), MP_ROM_PTR(&mod_trezorcrypto_HDNode_public_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_address), MP_ROM_PTR(&mod_trezorcrypto_HDNode_address_obj) },
    { MP_ROM_QSTR(MP_QSTR_nem_address), MP_ROM_PTR(&mod_trezorcrypto_HDNode_nem_address_obj) },
    { MP_ROM_QSTR(MP_QSTR_nem_encrypt), MP_ROM_PTR(&mod_trezorcrypto_HDNode_nem_encrypt_obj) },
    { MP_ROM_QSTR(MP_QSTR_ethereum_pubkeyhash), MP_ROM_PTR(&mod_trezorcrypto_HDNode_ethereum_pubkeyhash_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_HDNode_locals_dict, mod_trezorcrypto_HDNode_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_HDNode_type = {
    { &mp_type_type },
    .name = MP_QSTR_HDNode,
    .make_new = mod_trezorcrypto_HDNode_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_HDNode_locals_dict,
};

/// def deserialize(self, value: str, version_public: int, version_private: int) -> HDNode:
///     '''
///     Construct a BIP0032 HD node from a base58-serialized value.
///     '''
STATIC mp_obj_t mod_trezorcrypto_bip32_deserialize(mp_obj_t value, mp_obj_t version_public, mp_obj_t version_private) {
    mp_buffer_info_t valueb;
    mp_get_buffer_raise(value, &valueb, MP_BUFFER_READ);
    if (valueb.len == 0) {
        mp_raise_ValueError("Invalid value");
    }
    uint32_t vpub = trezor_obj_get_uint(version_public);
    uint32_t vpriv = trezor_obj_get_uint(version_private);
    HDNode hdnode;
    uint32_t fingerprint;
    if (hdnode_deserialize(valueb.buf, vpub, vpriv, SECP256K1_NAME, &hdnode, &fingerprint) < 0) {
        mp_raise_ValueError("Failed to deserialize");
    }

    mp_obj_HDNode_t *o = m_new_obj(mp_obj_HDNode_t);
    o->base.type = &mod_trezorcrypto_HDNode_type;
    o->hdnode = hdnode;
    o->fingerprint = fingerprint;
    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_bip32_deserialize_obj, mod_trezorcrypto_bip32_deserialize);

/// def from_seed(seed: bytes, curve_name: str) -> HDNode:
///     '''
///     Construct a BIP0032 HD node from a BIP0039 seed value.
///     '''
STATIC mp_obj_t mod_trezorcrypto_bip32_from_seed(mp_obj_t seed, mp_obj_t curve_name) {
    mp_buffer_info_t seedb;
    mp_get_buffer_raise(seed, &seedb, MP_BUFFER_READ);
    if (seedb.len == 0) {
        mp_raise_ValueError("Invalid seed");
    }
    mp_buffer_info_t curveb;
    mp_get_buffer_raise(curve_name, &curveb, MP_BUFFER_READ);
    if (curveb.len == 0) {
        mp_raise_ValueError("Invalid curve name");
    }
    HDNode hdnode;
    if (!hdnode_from_seed(seedb.buf, seedb.len, curveb.buf, &hdnode)) {
        mp_raise_ValueError("Failed to derive the root node");
    }
    mp_obj_HDNode_t *o = m_new_obj(mp_obj_HDNode_t);
    o->base.type = &mod_trezorcrypto_HDNode_type;
    o->hdnode = hdnode;
    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_bip32_from_seed_obj, mod_trezorcrypto_bip32_from_seed);

/// def from_mnemonic_cardano(mnemonic: str) -> bytes:
///     '''
///     Convert mnemonic to hdnode
//      '''
STATIC mp_obj_t mod_trezorcrypto_bip32_from_mnemonic_cardano(mp_obj_t mnemonic) {
    mp_buffer_info_t mnemo;
    mp_get_buffer_raise(mnemonic, &mnemo, MP_BUFFER_READ);
    HDNode hdnode;
    const char *pmnemonic = mnemo.len > 0 ? mnemo.buf : "";
    uint8_t entropy[66];
    int entropy_len = mnemonic_to_entropy(pmnemonic, entropy + 2);

    if (entropy_len == 0) {
        mp_raise_ValueError("Invalid mnemonic");
    }

    const int res = hdnode_from_seed_cardano((const uint8_t *)"", 0, entropy, entropy_len / 8, &hdnode);
    if (!res) {
        mp_raise_ValueError("Secret key generation from mnemonic is looping forever");
    }else if(res == -1){
        mp_raise_ValueError("Invalid mnemonic");
    }

    mp_obj_HDNode_t *o = m_new_obj(mp_obj_HDNode_t);
    o->base.type = &mod_trezorcrypto_HDNode_type;
    o->hdnode = hdnode;
    return MP_OBJ_FROM_PTR(o);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip32_from_mnemonic_cardano_obj,
        mod_trezorcrypto_bip32_from_mnemonic_cardano);


STATIC const mp_rom_map_elem_t mod_trezorcrypto_bip32_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip32) },
    { MP_ROM_QSTR(MP_QSTR_HDNode), MP_ROM_PTR(&mod_trezorcrypto_HDNode_type) },
    { MP_ROM_QSTR(MP_QSTR_deserialize), MP_ROM_PTR(&mod_trezorcrypto_bip32_deserialize_obj) },
    { MP_ROM_QSTR(MP_QSTR_from_seed), MP_ROM_PTR(&mod_trezorcrypto_bip32_from_seed_obj) },
    { MP_ROM_QSTR(MP_QSTR_from_mnemonic_cardano), MP_ROM_PTR(&mod_trezorcrypto_bip32_from_mnemonic_cardano_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_bip32_globals, mod_trezorcrypto_bip32_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_bip32_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_bip32_globals,
};
