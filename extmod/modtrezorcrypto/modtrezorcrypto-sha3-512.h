/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "sha3.h"

#define HASH_SHA3_512_BLOCK_SIZE   128
#define HASH_SHA3_512_DIGEST_SIZE  64

// class Sha3_512(object):
typedef struct _mp_obj_Sha3_512_t {
    mp_obj_base_t base;
    sha3_ctx ctx;
} mp_obj_Sha3_512_t;

STATIC mp_obj_t mod_TrezorCrypto_Sha3_512_update(mp_obj_t self, mp_obj_t data);

// def Sha3_512.__init__(self, data: bytes = None)
STATIC mp_obj_t mod_TrezorCrypto_Sha3_512_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 1, false);
    mp_obj_Sha3_512_t *o = m_new_obj(mp_obj_Sha3_512_t);
    o->base.type = type;
    rhash_sha3_512_init(&(o->ctx));
    // constructor called with bytes/str as first parameter
    if (n_args == 1) {
        mod_TrezorCrypto_Sha3_512_update(MP_OBJ_FROM_PTR(o), args[0]);
    }
    return MP_OBJ_FROM_PTR(o);
}

// def Sha3_512.update(self, data: bytes) -> None
STATIC mp_obj_t mod_TrezorCrypto_Sha3_512_update(mp_obj_t self, mp_obj_t data) {
    mp_obj_Sha3_512_t *o = MP_OBJ_TO_PTR(self);
    mp_buffer_info_t databuf;
    mp_get_buffer_raise(data, &databuf, MP_BUFFER_READ);
    rhash_sha3_update(&(o->ctx), databuf.buf, databuf.len);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Sha3_512_update_obj, mod_TrezorCrypto_Sha3_512_update);

// def Sha3_512.digest(self) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Sha3_512_digest(mp_obj_t self) {
    mp_obj_Sha3_512_t *o = MP_OBJ_TO_PTR(self);
    vstr_t vstr;
    vstr_init_len(&vstr, HASH_SHA3_512_DIGEST_SIZE);
    sha3_ctx ctx;
    memcpy(&ctx, &(o->ctx), sizeof(sha3_ctx));
    rhash_sha3_final(&ctx, (uint8_t *)vstr.buf);
    memset(&ctx, 0, sizeof(sha3_ctx));
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_Sha3_512_digest_obj, mod_TrezorCrypto_Sha3_512_digest);

// def Sha3_512.__del__(self) -> None
STATIC mp_obj_t mod_TrezorCrypto_Sha3_512___del__(mp_obj_t self) {
    mp_obj_Sha3_512_t *o = MP_OBJ_TO_PTR(self);
    memset(&(o->ctx), 0, sizeof(sha3_ctx));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_Sha3_512___del___obj, mod_TrezorCrypto_Sha3_512___del__);

// Sha3_512 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Sha3_512_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_512_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_512_digest_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_512___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_block_size), MP_OBJ_NEW_SMALL_INT(HASH_SHA3_512_BLOCK_SIZE) },
    { MP_ROM_QSTR(MP_QSTR_digest_size), MP_OBJ_NEW_SMALL_INT(HASH_SHA3_512_DIGEST_SIZE) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Sha3_512_locals_dict, mod_TrezorCrypto_Sha3_512_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Sha3_512_type = {
    { &mp_type_type },
    .name = MP_QSTR_Sha3_512,
    .make_new = mod_TrezorCrypto_Sha3_512_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Sha3_512_locals_dict,
};
