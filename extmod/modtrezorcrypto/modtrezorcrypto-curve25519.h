/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/curve25519-donna/curve25519-donna.h"

typedef struct _mp_obj_Curve25519_t {
    mp_obj_base_t base;
} mp_obj_Curve25519_t;

STATIC mp_obj_t mod_TrezorCrypto_Curve25519_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Curve25519_t *o = m_new_obj(mp_obj_Curve25519_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.crypto.curve.curve25519.multiply(secret_key: bytes, public_key: bytes) -> bytes:
///     '''
///     Multiplies point defined by public_key with scalar defined by secret_key
///     Useful for ECDH
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Curve25519_multiply(mp_obj_t self, mp_obj_t secret_key, mp_obj_t public_key) {
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
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Curve25519_multiply_obj, mod_TrezorCrypto_Curve25519_multiply);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Curve25519_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_multiply), MP_ROM_PTR(&mod_TrezorCrypto_Curve25519_multiply_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Curve25519_locals_dict, mod_TrezorCrypto_Curve25519_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Curve25519_type = {
    { &mp_type_type },
    .name = MP_QSTR_Curve25519,
    .make_new = mod_TrezorCrypto_Curve25519_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Curve25519_locals_dict,
};
