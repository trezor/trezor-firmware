/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "rand.h"

typedef struct _mp_obj_Random_t {
    mp_obj_base_t base;
} mp_obj_Random_t;

STATIC mp_obj_t mod_TrezorCrypto_Random_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Random_t *o = m_new_obj(mp_obj_Random_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.crypto.random.uniform(n: int) -> int:
///     '''
///     Compute uniform random number from interval 0 ... n - 1
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Random_uniform(mp_obj_t self, mp_obj_t n) {
    uint32_t nn = mp_obj_get_int_truncated(n);
    if (nn == 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Maximum can't be zero"));
    }
    return mp_obj_new_int_from_uint(random_uniform(nn));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Random_uniform_obj, mod_TrezorCrypto_Random_uniform);

/// def trezor.crypto.random.bytes(len: int) -> bytes:
///     '''
///     Generate random bytes sequence of length len
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Random_bytes(mp_obj_t self, mp_obj_t len) {
    uint32_t l = mp_obj_get_int(len);
    vstr_t vstr;
    vstr_init_len(&vstr, l);
    random_buffer((uint8_t *)vstr.buf, l);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Random_bytes_obj, mod_TrezorCrypto_Random_bytes);

/// def trezor.crypto.random.shuffle(data: list) -> None:
///     '''
///     Shuffles items of given list (in-place)
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Random_shuffle(mp_obj_t self, mp_obj_t data) {
    mp_uint_t item_cnt;
    mp_obj_t *items;
    if (MP_OBJ_IS_TYPE(data, &mp_type_list)) {
        mp_obj_list_get(data, &item_cnt, &items);
    } else {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "List expected"));
    }
    if (item_cnt > 256) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Maximum list size is 256 items"));
    }
    random_permute(items, sizeof(mp_obj_t *), item_cnt);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Random_shuffle_obj, mod_TrezorCrypto_Random_shuffle);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Random_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_uniform), MP_ROM_PTR(&mod_TrezorCrypto_Random_uniform_obj) },
    { MP_ROM_QSTR(MP_QSTR_bytes), MP_ROM_PTR(&mod_TrezorCrypto_Random_bytes_obj) },
    { MP_ROM_QSTR(MP_QSTR_shuffle), MP_ROM_PTR(&mod_TrezorCrypto_Random_shuffle_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Random_locals_dict, mod_TrezorCrypto_Random_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Random_type = {
    { &mp_type_type },
    .name = MP_QSTR_Random,
    .make_new = mod_TrezorCrypto_Random_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Random_locals_dict,
};



