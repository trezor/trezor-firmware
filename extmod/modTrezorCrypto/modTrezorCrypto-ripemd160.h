/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/ripemd160.h"

// class Ripemd160(object):
typedef struct _mp_obj_Ripemd160_t {
    mp_obj_base_t base;
    uint8_t hash[20];
} mp_obj_Ripemd160_t;

// def Ripemd160.__init__(self, data: bytes = None)
STATIC mp_obj_t mod_TrezorCrypto_Ripemd160_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_Ripemd160_t *o = m_new_obj(mp_obj_Ripemd160_t);
    o->base.type = type;
    // constructor called with bytes/str as first parameter
    if (n_args == 1) {
        if (!MP_OBJ_IS_STR_OR_BYTES(args[0])) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_TypeError, "Invalid argument"));
        }
        GET_STR_DATA_LEN(args[0], data, datalen);
        ripemd160(data, datalen, o->hash);
    } else {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_TypeError, "Invalid arguments"));
    }
    return MP_OBJ_FROM_PTR(o);
}

// no update for now ...

// def Ripemd160.digest(self) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Ripemd160_digest(mp_obj_t self) {
    mp_obj_Ripemd160_t *o = MP_OBJ_TO_PTR(self);
    vstr_t vstr;
    vstr_init_len(&vstr, 20); // 160 bit = 20 bytes
    memcpy(vstr.buf, o->hash, 20);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_Ripemd160_digest_obj, mod_TrezorCrypto_Ripemd160_digest);

// Ripemd160 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Ripemd160_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&mod_TrezorCrypto_Ripemd160_digest_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Ripemd160_locals_dict, mod_TrezorCrypto_Ripemd160_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Ripemd160_type = {
    { &mp_type_type },
    .name = MP_QSTR_Ripemd160,
    .make_new = mod_TrezorCrypto_Ripemd160_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Ripemd160_locals_dict,
};
