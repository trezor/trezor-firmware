/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "py/runtime.h"
#include "py/mphal.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORCONFIG

#include "embed/extmod/trezorobj.h"

#include "norcow.h"
#include "storage.h"

/// def init() -> None:
///     '''
///     Initializes the storage.  Must be called before any other method is
///     called from this module!
///     '''
STATIC mp_obj_t mod_trezorconfig_init(void) {
    storage_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_init_obj, mod_trezorconfig_init);

/// def check_pin(pin: int, waitcallback: (int, int -> None)) -> bool:
///     '''
///     Check the given PIN. Returns True on success, False on failure.
///     '''
STATIC mp_obj_t mod_trezorconfig_check_pin(mp_obj_t pin, mp_obj_t waitcallback) {
    uint32_t pin_i = trezor_obj_get_uint(pin);
    if (sectrue != storage_check_pin(pin_i, waitcallback)) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_check_pin_obj, mod_trezorconfig_check_pin);

/// def unlock(pin: int, waitcallback: (int, int -> None)) -> bool:
///     '''
///     Attempts to unlock the storage with given PIN.  Returns True on
///     success, False on failure.
///     '''
STATIC mp_obj_t mod_trezorconfig_unlock(mp_obj_t pin, mp_obj_t waitcallback) {
    uint32_t pin_i = trezor_obj_get_uint(pin);
    if (sectrue != storage_unlock(pin_i, waitcallback)) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_unlock_obj, mod_trezorconfig_unlock);

/// def has_pin() -> bool:
///     '''
///     Returns True if storage has a configured PIN, False otherwise.
///     '''
STATIC mp_obj_t mod_trezorconfig_has_pin(void) {
    if (sectrue != storage_has_pin()) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_has_pin_obj, mod_trezorconfig_has_pin);

/// def change_pin(pin: int, newpin: int, waitcallback: (int, int -> None)) -> bool:
///     '''
///     Change PIN. Returns True on success, False on failure.
///     '''
STATIC mp_obj_t mod_trezorconfig_change_pin(mp_obj_t pin, mp_obj_t newpin, mp_obj_t waitcallback) {
    uint32_t pin_i = trezor_obj_get_uint(pin);
    uint32_t newpin_i = trezor_obj_get_uint(newpin);
    if (sectrue != storage_change_pin(pin_i, newpin_i, waitcallback)) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorconfig_change_pin_obj, mod_trezorconfig_change_pin);

/// def get(app: int, key: int, public: bool=False) -> bytes:
///     '''
///     Gets a value of given key for given app (or empty bytes if not set).
///     '''
STATIC mp_obj_t mod_trezorconfig_get(size_t n_args, const mp_obj_t *args) {
    uint8_t app = trezor_obj_get_uint8(args[0]) & 0x7F;
    uint8_t key = trezor_obj_get_uint8(args[1]);
    if (n_args > 2 && args[2] == mp_const_true) {
        app |= 0x80;
    }
    uint16_t appkey = (app << 8) | key;
    uint16_t len = 0;
    const void *val;
    if (sectrue != storage_get(appkey, &val, &len) || len == 0) {
        return mp_const_empty_bytes;
    }
    return mp_obj_new_bytes(val, len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_get_obj, 2, 3, mod_trezorconfig_get);

/// def set(app: int, key: int, value: bytes, public: bool=False) -> None:
///     '''
///     Sets a value of given key for given app.
///     '''
STATIC mp_obj_t mod_trezorconfig_set(size_t n_args, const mp_obj_t *args) {
    uint8_t app = trezor_obj_get_uint8(args[0]) & 0x7F;
    uint8_t key = trezor_obj_get_uint8(args[1]);
    if (n_args > 3 && args[3] == mp_const_true) {
        app |= 0x80;
    }
    uint16_t appkey = (app << 8) | key;
    mp_buffer_info_t value;
    mp_get_buffer_raise(args[2], &value, MP_BUFFER_READ);
    if (sectrue != storage_set(appkey, value.buf, value.len)) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_set_obj, 3, 4, mod_trezorconfig_set);

/// def wipe() -> None:
///     '''
///     Erases the whole config. Use with caution!
///     '''
STATIC mp_obj_t mod_trezorconfig_wipe(void) {
    storage_wipe();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_wipe_obj, mod_trezorconfig_wipe);

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezorconfig_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_check_pin), MP_ROM_PTR(&mod_trezorconfig_check_pin_obj) },
    { MP_ROM_QSTR(MP_QSTR_unlock), MP_ROM_PTR(&mod_trezorconfig_unlock_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_pin), MP_ROM_PTR(&mod_trezorconfig_has_pin_obj) },
    { MP_ROM_QSTR(MP_QSTR_change_pin), MP_ROM_PTR(&mod_trezorconfig_change_pin_obj) },
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
