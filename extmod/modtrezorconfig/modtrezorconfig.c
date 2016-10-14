/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORCONFIG


// temporary function stubs from norcow
void norcow_init(void) { }
bool norcow_get(uint16_t key, const void **val, uint32_t *len) { *val = "Works!"; *len = 6; return true; }
bool norcow_set(uint16_t key, const void *val, uint32_t len) { return true; }
// end


typedef struct _mp_obj_Config_t {
    mp_obj_base_t base;
} mp_obj_Config_t;

STATIC mp_obj_t mod_TrezorConfig_Config_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Config_t *o = m_new_obj(mp_obj_Config_t);
    o->base.type = type;
    norcow_init();
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.config.get(app: int, key: int) -> bytes:
///     '''
///     Gets a value of given key for given app (or None if not set).
///     '''
STATIC mp_obj_t mod_TrezorConfig_Config_get(mp_obj_t self, mp_obj_t app, mp_obj_t key) {
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k;
    const void *val;
    uint32_t len;
    bool r = norcow_get(appkey, &val, &len);
    if (!r) return mp_const_none;
    vstr_t vstr;
    vstr_init_len(&vstr, len);
    memcpy(vstr.buf, val, len);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorConfig_Config_get_obj, mod_TrezorConfig_Config_get);

/// def trezor.config.set(app: int, key: int, value: bytes) -> None:
///     '''
///     Sets a value of given key for given app.
///     Returns True on success.
///     '''
STATIC mp_obj_t mod_TrezorConfig_Config_set(size_t n_args, const mp_obj_t *args) {
    uint8_t a = mp_obj_get_int(args[1]);
    uint8_t k = mp_obj_get_int(args[2]);
    uint16_t appkey = a << 8 | k;
    mp_buffer_info_t value;
    mp_get_buffer_raise(args[3], &value, MP_BUFFER_READ);
    bool r = norcow_set(appkey, value.buf, value.len);
    if (!r) {
        mp_raise_ValueError("Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorConfig_Config_set_obj, 4, 4, mod_TrezorConfig_Config_set);

STATIC const mp_rom_map_elem_t mod_TrezorConfig_Config_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_TrezorConfig_Config_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_TrezorConfig_Config_set_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorConfig_Config_locals_dict, mod_TrezorConfig_Config_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorConfig_Config_type = {
    { &mp_type_type },
    .name = MP_QSTR_Config,
    .make_new = mod_TrezorConfig_Config_make_new,
    .locals_dict = (void*)&mod_TrezorConfig_Config_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_TrezorConfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorConfig) },
    { MP_ROM_QSTR(MP_QSTR_Config), MP_ROM_PTR(&mod_TrezorConfig_Config_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorConfig_globals, mp_module_TrezorConfig_globals_table);

const mp_obj_module_t mp_module_TrezorConfig = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorConfig_globals,
};

#endif // MICROPY_PY_TREZORCONFIG
