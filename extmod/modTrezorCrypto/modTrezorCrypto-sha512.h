/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "trezor-crypto/sha2.h"

// class Sha512(object):
typedef struct _mp_obj_Sha512_t {
    mp_obj_base_t base;
} mp_obj_Sha512_t;

// def Sha512.__init__(self):
STATIC mp_obj_t mod_TrezorCrypto_Sha512_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_Sha512_t *o = m_new_obj(mp_obj_Sha512_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Sha512.hash(self, data: bytes) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Sha512_hash(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t databuf;
    mp_get_buffer_raise(data, &databuf, MP_BUFFER_READ);
    vstr_t vstr;
    vstr_init_len(&vstr, 64); // 512 bit = 64 bytes
    sha512_Raw(databuf.buf, databuf.len, (uint8_t *)vstr.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Sha512_hash_obj, mod_TrezorCrypto_Sha512_hash);

// Sha512 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Sha512_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_hash), MP_ROM_PTR(&mod_TrezorCrypto_Sha512_hash_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Sha512_locals_dict, mod_TrezorCrypto_Sha512_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Sha512_type = {
    { &mp_type_type },
    .name = MP_QSTR_Sha512,
    .make_new = mod_TrezorCrypto_Sha512_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Sha512_locals_dict,
};
