/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "ed25519-donna/ed25519.h"

#include "rand.h"

/// def generate_secret() -> bytes:
///     '''
///     Generate secret key.
///     '''
STATIC mp_obj_t mod_trezorcrypto_curve25519_generate_secret() {
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    random_buffer((uint8_t *)vstr.buf, 32);
    // taken from https://cr.yp.to/ecdh.html
    vstr.buf[0] &= 248;
    vstr.buf[31] &= 127;
    vstr.buf[31] |= 64;
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_curve25519_generate_secret_obj, mod_trezorcrypto_curve25519_generate_secret);

/// def publickey(secret_key: bytes) -> bytes:
///     '''
///     Computes public key from secret key.
///     '''
STATIC mp_obj_t mod_trezorcrypto_curve25519_publickey(mp_obj_t secret_key) {
    mp_buffer_info_t sk;
    mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    curve25519_scalarmult_basepoint((uint8_t *)vstr.buf, (const uint8_t *)sk.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_curve25519_publickey_obj, mod_trezorcrypto_curve25519_publickey);

/// def multiply(secret_key: bytes, public_key: bytes) -> bytes:
///     '''
///     Multiplies point defined by public_key with scalar defined by secret_key.
///     Useful for ECDH.
///     '''
STATIC mp_obj_t mod_trezorcrypto_curve25519_multiply(mp_obj_t secret_key, mp_obj_t public_key) {
    mp_buffer_info_t sk, pk;
    mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
    mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    if (pk.len != 32) {
        mp_raise_ValueError("Invalid length of public key");
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    curve25519_scalarmult((uint8_t *)vstr.buf, (const uint8_t *)sk.buf, (const uint8_t *)pk.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_curve25519_multiply_obj, mod_trezorcrypto_curve25519_multiply);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_curve25519_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_curve25519) },
    { MP_ROM_QSTR(MP_QSTR_generate_secret), MP_ROM_PTR(&mod_trezorcrypto_curve25519_generate_secret_obj) },
    { MP_ROM_QSTR(MP_QSTR_publickey), MP_ROM_PTR(&mod_trezorcrypto_curve25519_publickey_obj) },
    { MP_ROM_QSTR(MP_QSTR_multiply), MP_ROM_PTR(&mod_trezorcrypto_curve25519_multiply_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_curve25519_globals, mod_trezorcrypto_curve25519_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_curve25519_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_curve25519_globals,
};
