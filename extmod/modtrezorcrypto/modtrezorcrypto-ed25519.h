/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/ed25519-donna/ed25519.h"

// class Ed25519(object):
typedef struct _mp_obj_Ed25519_t {
    mp_obj_base_t base;
} mp_obj_Ed25519_t;

// def Ed25519.__init__(self)
STATIC mp_obj_t mod_TrezorCrypto_Ed25519_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Ed25519_t *o = m_new_obj(mp_obj_Ed25519_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Ed25519.publickey(self, secret_key: bytes) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Ed25519_publickey(mp_obj_t self, mp_obj_t secret_key) {
    mp_buffer_info_t skbuf;
    mp_get_buffer_raise(secret_key, &skbuf, MP_BUFFER_READ);
    if (skbuf.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of secret key"));
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    ed25519_publickey(*(const ed25519_secret_key *)skbuf.buf, *(ed25519_public_key *)vstr.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Ed25519_publickey_obj, mod_TrezorCrypto_Ed25519_publickey);

// def Ed25519.sign(self, secret_key: bytes, message: bytes) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Ed25519_sign(mp_obj_t self, mp_obj_t secret_key, mp_obj_t message) {
    mp_buffer_info_t skbuf, messagebuf;
    mp_get_buffer_raise(secret_key, &skbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(message, &messagebuf, MP_BUFFER_READ);
    if (skbuf.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of secret key"));
    }
    ed25519_public_key pk;
    ed25519_publickey(*(const ed25519_secret_key *)skbuf.buf, pk);
    vstr_t vstr;
    vstr_init_len(&vstr, 64);
    ed25519_sign(messagebuf.buf, messagebuf.len, *(const ed25519_secret_key *)skbuf.buf, pk, *(ed25519_signature *)vstr.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Ed25519_sign_obj, mod_TrezorCrypto_Ed25519_sign);

// def Ed25519.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
STATIC mp_obj_t mod_TrezorCrypto_Ed25519_verify(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t pkbuf, sigbuf, messagebuf;
    mp_get_buffer_raise(args[1], &pkbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &sigbuf, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &messagebuf, MP_BUFFER_READ);
    if (pkbuf.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of public key"));
    }
    if (sigbuf.len != 64) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of signature"));
    }
    return (0 == ed25519_sign_open(messagebuf.buf, messagebuf.len, *(const ed25519_public_key *)pkbuf.buf, *(const ed25519_signature *)sigbuf.buf)) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_Ed25519_verify_obj, 4, 4, mod_TrezorCrypto_Ed25519_verify);

// Ed25519 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Ed25519_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_publickey), MP_ROM_PTR(&mod_TrezorCrypto_Ed25519_publickey_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_TrezorCrypto_Ed25519_sign_obj) },
    { MP_ROM_QSTR(MP_QSTR_verify), MP_ROM_PTR(&mod_TrezorCrypto_Ed25519_verify_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Ed25519_locals_dict, mod_TrezorCrypto_Ed25519_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Ed25519_type = {
    { &mp_type_type },
    .name = MP_QSTR_Ed25519,
    .make_new = mod_TrezorCrypto_Ed25519_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Ed25519_locals_dict,
};
