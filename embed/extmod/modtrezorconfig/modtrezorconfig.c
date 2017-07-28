/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/runtime.h"

#if MICROPY_PY_TREZORCONFIG

#include <stdint.h>
#include <string.h>
#include "norcow.h"

static bool initialized = false;

/// def init() -> None:
///     '''
///     Initializes the storage. Must be called before any other method is called from this module!
///     '''
STATIC mp_obj_t mod_trezorconfig_init(void) {
    bool r = norcow_init();
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not initialize config module");
    }
    initialized = true;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_init_obj, mod_trezorconfig_init);

/// def get(app: int, key: int) -> bytes:
///     '''
///     Gets a value of given key for given app (or empty bytes if not set).
///     '''
STATIC mp_obj_t mod_trezorconfig_get(mp_obj_t app, mp_obj_t key) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k, len;
    const void *val;
    bool r = norcow_get(appkey, &val, &len);
    if (!r || len == 0) {
        return mp_const_empty_bytes;
    }
    vstr_t vstr;
    vstr_init_len(&vstr, len);
    memcpy(vstr.buf, val, len);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_get_obj, mod_trezorconfig_get);

/// def set(app: int, key: int, value: bytes) -> None:
///     '''
///     Sets a value of given key for given app.
///     '''
STATIC mp_obj_t mod_trezorconfig_set(mp_obj_t app, mp_obj_t key, mp_obj_t value) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k;
    mp_buffer_info_t v;
    mp_get_buffer_raise(value, &v, MP_BUFFER_READ);
    bool r = norcow_set(appkey, v.buf, v.len);
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorconfig_set_obj, mod_trezorconfig_set);

/// def wipe() -> None:
///     '''
///     Erases the whole config. Use with caution!
///     '''
STATIC mp_obj_t mod_trezorconfig_wipe(void) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    bool r = norcow_wipe();
    if (!r) {
       mp_raise_msg(&mp_type_RuntimeError, "Could not wipe storage");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_wipe_obj, mod_trezorconfig_wipe);

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezorconfig_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezorconfig_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorconfig_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_wipe), MP_ROM_PTR(&mod_trezorconfig_wipe_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals, mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezorconfig_globals,
};

#endif // MICROPY_PY_TREZORCONFIG
