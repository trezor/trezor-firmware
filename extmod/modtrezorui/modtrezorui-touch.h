/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

// touch callbacks

mp_obj_t touch_start_callback = mp_const_none;
mp_obj_t touch_move_callback = mp_const_none;
mp_obj_t touch_end_callback = mp_const_none;

void touch_start(mp_int_t x, mp_int_t y) {
    if (touch_start_callback != mp_const_none) {
        mp_call_function_2(touch_start_callback, MP_OBJ_NEW_SMALL_INT(x), MP_OBJ_NEW_SMALL_INT(y));
    }
}

void touch_move(mp_int_t x, mp_int_t y) {
    if (touch_move_callback != mp_const_none) {
        mp_call_function_2(touch_move_callback, MP_OBJ_NEW_SMALL_INT(x), MP_OBJ_NEW_SMALL_INT(y));
    }
}

void touch_end(mp_int_t x, mp_int_t y) {
    if (touch_end_callback != mp_const_none) {
        mp_call_function_2(touch_end_callback, MP_OBJ_NEW_SMALL_INT(x), MP_OBJ_NEW_SMALL_INT(y));
    }
}

// class Touch(object):
typedef struct _mp_obj_Touch_t {
    mp_obj_base_t base;
} mp_obj_Touch_t;

// def Touch.__init__(self)
STATIC mp_obj_t mod_TrezorUi_Touch_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Touch_t *o = m_new_obj(mp_obj_Touch_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Touch.start(self, callback) -> None
STATIC mp_obj_t mod_TrezorUi_Touch_start(mp_obj_t self, mp_obj_t callback) {
    touch_start_callback = callback;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUi_Touch_start_obj, mod_TrezorUi_Touch_start);

// def Touch.move(self, callback) -> None
STATIC mp_obj_t mod_TrezorUi_Touch_move(mp_obj_t self, mp_obj_t callback) {
    touch_move_callback = callback;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUi_Touch_move_obj, mod_TrezorUi_Touch_move);

// def Touch.end(self, callback) -> None
STATIC mp_obj_t mod_TrezorUi_Touch_end(mp_obj_t self, mp_obj_t callback) {
    touch_end_callback = callback;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUi_Touch_end_obj, mod_TrezorUi_Touch_end);

// Touch stuff

STATIC const mp_rom_map_elem_t mod_TrezorUi_Touch_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&mod_TrezorUi_Touch_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_move), MP_ROM_PTR(&mod_TrezorUi_Touch_move_obj) },
    { MP_ROM_QSTR(MP_QSTR_end), MP_ROM_PTR(&mod_TrezorUi_Touch_end_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorUi_Touch_locals_dict, mod_TrezorUi_Touch_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorUi_Touch_type = {
    { &mp_type_type },
    .name = MP_QSTR_Touch,
    .make_new = mod_TrezorUi_Touch_make_new,
    .locals_dict = (void*)&mod_TrezorUi_Touch_locals_dict,
};
