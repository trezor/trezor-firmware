/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "sbu.h"

/// class SBU:
///     '''
///     '''
typedef struct _mp_obj_SBU_t {
    mp_obj_base_t base;
} mp_obj_SBU_t;

/// def __init__(self) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezorio_SBU_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_SBU_t *o = m_new_obj(mp_obj_SBU_t);
    o->base.type = type;
    sbu_init();
    return MP_OBJ_FROM_PTR(o);
}

/// def set(self, sbu1: bool, sbu2: bool) -> None:
///     '''
///     Sets SBU wires to sbu1 and sbu2 values respectively
///     '''
STATIC mp_obj_t mod_trezorio_SBU_set(mp_obj_t self, mp_obj_t sbu1, mp_obj_t sbu2) {
    sbu_set(mp_obj_is_true(sbu1), mp_obj_is_true(sbu2));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_SBU_set_obj, mod_trezorio_SBU_set);

STATIC const mp_rom_map_elem_t mod_trezorio_SBU_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorio_SBU_set_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_SBU_locals_dict, mod_trezorio_SBU_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_SBU_type = {
    { &mp_type_type },
    .name = MP_QSTR_SBU,
    .make_new = mod_trezorio_SBU_make_new,
    .locals_dict = (void*)&mod_trezorio_SBU_locals_dict,
};
