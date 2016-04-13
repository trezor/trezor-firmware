/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/sha2.h"

// class Sha256(object):
typedef struct _mp_obj_Sha256_t {
    mp_obj_base_t base;
    SHA256_CTX ctx;
} mp_obj_Sha256_t;

// def Sha256.__init__(self, data: bytes = None)
STATIC mp_obj_t mod_TrezorCrypto_Sha256_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_Sha256_t *o = m_new_obj(mp_obj_Sha256_t);
    o->base.type = type;
    sha256_Init(&(o->ctx));
    // constructor called with bytes/str as first parameter
    if (n_args == 1) {
        if (!MP_OBJ_IS_STR_OR_BYTES(args[0])) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_TypeError, "Invalid argument"));
        }
        GET_STR_DATA_LEN(args[0], data, datalen);
        sha256_Update(&(o->ctx), data, datalen);
    } else if (n_args != 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_TypeError, "Invalid arguments"));
    }
    return MP_OBJ_FROM_PTR(o);
}

// def Sha256.update(self, data: bytes) -> None
STATIC mp_obj_t mod_TrezorCrypto_Sha256_update(mp_obj_t self, mp_obj_t data) {
    mp_obj_Sha256_t *o = MP_OBJ_TO_PTR(self);
    mp_buffer_info_t databuf;
    mp_get_buffer_raise(data, &databuf, MP_BUFFER_READ);
    sha256_Update(&(o->ctx), databuf.buf, databuf.len);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Sha256_update_obj, mod_TrezorCrypto_Sha256_update);

// def Sha256.digest(self) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Sha256_digest(mp_obj_t self) {
    mp_obj_Sha256_t *o = MP_OBJ_TO_PTR(self);
    vstr_t vstr;
    vstr_init_len(&vstr, 32); // 256 bit = 32 bytes
    sha256_Final((uint8_t *)vstr.buf, &(o->ctx));
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_Sha256_digest_obj, mod_TrezorCrypto_Sha256_digest);

// Sha256 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Sha256_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_TrezorCrypto_Sha256_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&mod_TrezorCrypto_Sha256_digest_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Sha256_locals_dict, mod_TrezorCrypto_Sha256_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Sha256_type = {
    { &mp_type_type },
    .name = MP_QSTR_Sha256,
    .make_new = mod_TrezorCrypto_Sha256_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Sha256_locals_dict,
};
