/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/ecdsa.h"
#include "trezor-crypto/secp256k1.h"

// class Secp256k1(object):
typedef struct _mp_obj_Secp256k1_t {
    mp_obj_base_t base;
} mp_obj_Secp256k1_t;

// def Secp256k1.__init__(self)
STATIC mp_obj_t mod_TrezorCrypto_Secp256k1_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Secp256k1_t *o = m_new_obj(mp_obj_Secp256k1_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Secp256k1.publickey(self, secret_key: bytes, compressed: bool=True) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Secp256k1_publickey(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t skbuf;
    mp_get_buffer_raise(args[1], &skbuf, MP_BUFFER_READ);
    if (skbuf.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of secret key"));
    }
    bool compressed = n_args < 3 || args[2] == mp_const_true;
    vstr_t vstr;
    if (compressed) {
        vstr_init_len(&vstr, 33);
        ecdsa_get_public_key33(&secp256k1, (const uint8_t *)skbuf.buf, (uint8_t *)vstr.buf);
    } else {
        vstr_init_len(&vstr, 65);
        ecdsa_get_public_key65(&secp256k1, (const uint8_t *)skbuf.buf, (uint8_t *)vstr.buf);
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_Secp256k1_publickey_obj, 2, 3, mod_TrezorCrypto_Secp256k1_publickey);

// def Secp256k1.sign(self, secret_key: bytes, message: bytes) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Secp256k1_sign(mp_obj_t self, mp_obj_t secret_key, mp_obj_t message) {
    mp_buffer_info_t skbuf, messagebuf;
    mp_get_buffer_raise(secret_key, &skbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(message, &messagebuf, MP_BUFFER_READ);
    if (skbuf.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of secret key"));
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 65);
    uint8_t pby;
    if (0 != ecdsa_sign(&secp256k1, (const uint8_t *)skbuf.buf, (const uint8_t *)messagebuf.buf, messagebuf.len, (uint8_t *)vstr.buf, &pby)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Signing failed"));
    }
    (void)pby;
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Secp256k1_sign_obj, mod_TrezorCrypto_Secp256k1_sign);

// def Secp256k1.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
STATIC mp_obj_t mod_TrezorCrypto_Secp256k1_verify(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t pkbuf, sigbuf, messagebuf;
    mp_get_buffer_raise(args[1], &pkbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &sigbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &messagebuf, MP_BUFFER_READ);
    if (pkbuf.len != 33 && pkbuf.len != 65) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of public key"));
    }
    if (sigbuf.len != 65) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of signature"));
    }
    return mp_obj_new_bool(0 == ecdsa_verify(&secp256k1, (const uint8_t *)pkbuf.buf, (const uint8_t *)sigbuf.buf, (const uint8_t *)messagebuf.buf, messagebuf.len));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_Secp256k1_verify_obj, 4, 4, mod_TrezorCrypto_Secp256k1_verify);

// Secp256k1 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Secp256k1_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_publickey), MP_ROM_PTR(&mod_TrezorCrypto_Secp256k1_publickey_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_TrezorCrypto_Secp256k1_sign_obj) },
    { MP_ROM_QSTR(MP_QSTR_verify), MP_ROM_PTR(&mod_TrezorCrypto_Secp256k1_verify_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Secp256k1_locals_dict, mod_TrezorCrypto_Secp256k1_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Secp256k1_type = {
    { &mp_type_type },
    .name = MP_QSTR_Secp256k1,
    .make_new = mod_TrezorCrypto_Secp256k1_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Secp256k1_locals_dict,
};
