/*
 * This file is part of the Trezor project, https://trezor.io/
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

#include <string.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#if MICROPY_PY_TREZORCONFIG

#include "embed/extmod/trezorobj.h"

#include "common.h"
#include "memzero.h"
#include "storage.h"

STATIC mp_obj_t ui_wait_callback = mp_const_none;

STATIC secbool wrapped_ui_wait_callback(uint32_t wait, uint32_t progress,
                                        const char *message) {
  if (mp_obj_is_callable(ui_wait_callback)) {
    mp_obj_t args[3] = {0};
    args[0] = mp_obj_new_int(wait);
    args[1] = mp_obj_new_int(progress);
    args[2] = mp_obj_new_str(message, strlen(message));
    if (mp_call_function_n_kw(ui_wait_callback, 3, 0, args) == mp_const_true) {
      return sectrue;
    }
  }
  return secfalse;
}

/// def init(
///    ui_wait_callback: Callable[[int, int, str], bool] = None
/// ) -> None:
///     """
///     Initializes the storage.  Must be called before any other method is
///     called from this module!
///     """
STATIC mp_obj_t mod_trezorconfig_init(size_t n_args, const mp_obj_t *args) {
  if (n_args > 0) {
    ui_wait_callback = args[0];
    storage_init(wrapped_ui_wait_callback, HW_ENTROPY_DATA, HW_ENTROPY_LEN);
  } else {
    storage_init(NULL, HW_ENTROPY_DATA, HW_ENTROPY_LEN);
  }
  memzero(HW_ENTROPY_DATA, sizeof(HW_ENTROPY_DATA));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_init_obj, 0, 1,
                                           mod_trezorconfig_init);

/// def unlock(pin: int, ext_salt: Optional[bytes]) -> bool:
///     """
///     Attempts to unlock the storage with the given PIN and external salt.
///     Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_unlock(mp_obj_t pin, mp_obj_t ext_salt) {
  uint32_t pin_i = trezor_obj_get_uint(pin);
  mp_buffer_info_t ext_salt_b = {0};
  ext_salt_b.buf = NULL;
  if (ext_salt != mp_const_none) {
    mp_get_buffer_raise(ext_salt, &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError, "Invalid length of external salt.");
  }

  if (sectrue != storage_unlock(pin_i, ext_salt_b.buf)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_unlock_obj,
                                 mod_trezorconfig_unlock);

/// def check_pin(pin: int, ext_salt: Optional[bytes]) -> bool:
///     """
///     Check the given PIN with the given external salt.
///     Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_check_pin(mp_obj_t pin, mp_obj_t ext_salt) {
  return mod_trezorconfig_unlock(pin, ext_salt);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_check_pin_obj,
                                 mod_trezorconfig_check_pin);

/// def lock() -> None:
///     """
///     Locks the storage.
///     """
STATIC mp_obj_t mod_trezorconfig_lock(void) {
  storage_lock();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_lock_obj,
                                 mod_trezorconfig_lock);

/// def is_unlocked() -> bool:
///     """
///     Returns True if storage is unlocked, False otherwise.
///     """
STATIC mp_obj_t mod_trezorconfig_is_unlocked(void) {
  if (sectrue != storage_is_unlocked()) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_is_unlocked_obj,
                                 mod_trezorconfig_is_unlocked);

/// def has_pin() -> bool:
///     """
///     Returns True if storage has a configured PIN, False otherwise.
///     """
STATIC mp_obj_t mod_trezorconfig_has_pin(void) {
  if (sectrue != storage_has_pin()) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_has_pin_obj,
                                 mod_trezorconfig_has_pin);

/// def get_pin_rem() -> int:
///     """
///     Returns the number of remaining PIN entry attempts.
///     """
STATIC mp_obj_t mod_trezorconfig_get_pin_rem(void) {
  return mp_obj_new_int_from_uint(storage_get_pin_rem());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_get_pin_rem_obj,
                                 mod_trezorconfig_get_pin_rem);

/// def change_pin(
///     oldpin: int,
///     newpin: int,
///     old_ext_salt: Optional[bytes],
///     new_ext_salt: Optional[bytes],
/// ) -> bool:
///     """
///     Change PIN and external salt. Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_change_pin(size_t n_args,
                                            const mp_obj_t *args) {
  uint32_t oldpin = trezor_obj_get_uint(args[0]);
  uint32_t newpin = trezor_obj_get_uint(args[1]);
  mp_buffer_info_t ext_salt_b = {0};
  const uint8_t *old_ext_salt = NULL;
  if (args[2] != mp_const_none) {
    mp_get_buffer_raise(args[2], &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError, "Invalid length of external salt.");
    old_ext_salt = ext_salt_b.buf;
  }
  const uint8_t *new_ext_salt = NULL;
  if (args[3] != mp_const_none) {
    mp_get_buffer_raise(args[3], &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError, "Invalid length of external salt.");
    new_ext_salt = ext_salt_b.buf;
  }

  if (sectrue !=
      storage_change_pin(oldpin, newpin, old_ext_salt, new_ext_salt)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_change_pin_obj, 4,
                                           4, mod_trezorconfig_change_pin);

/// def ensure_not_wipe_code(pin: int) -> None:
///     """
///     Wipes the device if the entered PIN is the wipe code.
///     """
STATIC mp_obj_t mod_trezorconfig_ensure_not_wipe_code(mp_obj_t pin) {
  uint32_t pin_i = trezor_obj_get_uint(pin);
  storage_ensure_not_wipe_code(pin_i);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorconfig_ensure_not_wipe_code_obj,
                                 mod_trezorconfig_ensure_not_wipe_code);

/// def has_wipe_code() -> bool:
///     """
///     Returns True if storage has a configured wipe code, False otherwise.
///     """
STATIC mp_obj_t mod_trezorconfig_has_wipe_code(void) {
  if (sectrue != storage_has_wipe_code()) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_has_wipe_code_obj,
                                 mod_trezorconfig_has_wipe_code);

/// def change_wipe_code(
///     pin: int,
///     ext_salt: Optional[bytes],
///     wipe_code: int,
/// ) -> bool:
///     """
///     Change wipe code. Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_change_wipe_code(size_t n_args,
                                                  const mp_obj_t *args) {
  uint32_t pin = trezor_obj_get_uint(args[0]);
  uint32_t wipe_code = trezor_obj_get_uint(args[2]);
  mp_buffer_info_t ext_salt_b = {0};
  const uint8_t *ext_salt = NULL;
  if (args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError, "Invalid length of external salt.");
    ext_salt = ext_salt_b.buf;
  }

  if (sectrue != storage_change_wipe_code(pin, ext_salt, wipe_code)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorconfig_change_wipe_code_obj, 3, 3,
    mod_trezorconfig_change_wipe_code);

/// def get(app: int, key: int, public: bool = False) -> Optional[bytes]:
///     """
///     Gets the value of the given key for the given app (or None if not set).
///     Raises a RuntimeError if decryption or authentication of the stored
///     value fails.
///     """
STATIC mp_obj_t mod_trezorconfig_get(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]) & FLAGS_APPID;
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 2 && args[2] == mp_const_true) {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  uint16_t len = 0;
  if (sectrue != storage_get(appkey, NULL, 0, &len)) {
    return mp_const_none;
  }
  if (len == 0) {
    return mp_const_empty_bytes;
  }
  vstr_t vstr = {0};
  vstr_init_len(&vstr, len);
  if (sectrue != storage_get(appkey, vstr.buf, vstr.len, &len)) {
    vstr_clear(&vstr);
    mp_raise_msg(&mp_type_RuntimeError, "Failed to get value from storage.");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_get_obj, 2, 3,
                                           mod_trezorconfig_get);

/// def set(app: int, key: int, value: bytes, public: bool = False) -> None:
///     """
///     Sets a value of given key for given app.
///     """
STATIC mp_obj_t mod_trezorconfig_set(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]) & FLAGS_APPID;
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 3 && args[3] == mp_const_true) {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  mp_buffer_info_t value;
  mp_get_buffer_raise(args[2], &value, MP_BUFFER_READ);
  if (sectrue != storage_set(appkey, value.buf, value.len)) {
    mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_set_obj, 3, 4,
                                           mod_trezorconfig_set);

/// def delete(app: int, key: int, public: bool = False) -> bool:
///     """
///     Deletes the given key of the given app.
///     """
STATIC mp_obj_t mod_trezorconfig_delete(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]) & FLAGS_APPID;
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 2 && args[2] == mp_const_true) {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  if (sectrue != storage_delete(appkey)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_delete_obj, 2, 3,
                                           mod_trezorconfig_delete);

/// def set_counter(
///     app: int, key: int, count: int, writable_locked: bool = False
/// ) -> bool:
///     """
///     Sets the given key of the given app as a counter with the given value.
///     """
STATIC mp_obj_t mod_trezorconfig_set_counter(size_t n_args,
                                             const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]) & FLAGS_APPID;
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 3 && args[3] == mp_const_true) {
    app |= FLAGS_WRITE;
  } else {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  if (args[2] == mp_const_none) {
    if (sectrue != storage_delete(appkey)) {
      return mp_const_false;
    }
  } else {
    uint32_t count = trezor_obj_get_uint(args[2]);
    if (sectrue != storage_set_counter(appkey, count)) {
      return mp_const_false;
    }
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_set_counter_obj, 3,
                                           4, mod_trezorconfig_set_counter);

/// def next_counter(
///    app: int, key: int, writable_locked: bool = False,
/// ) -> Optional[int]:
///     """
///     Increments the counter stored under the given key of the given app and
///     returns the new value.
///     """
STATIC mp_obj_t mod_trezorconfig_next_counter(size_t n_args,
                                              const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]) & FLAGS_APPID;
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 2 && args[2] == mp_const_true) {
    app |= FLAGS_WRITE;
  } else {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  uint32_t count = 0;
  if (sectrue != storage_next_counter(appkey, &count)) {
    return mp_const_none;
  }
  return mp_obj_new_int_from_uint(count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_next_counter_obj, 2,
                                           3, mod_trezorconfig_next_counter);

/// def wipe() -> None:
///     """
///     Erases the whole config. Use with caution!
///     """
STATIC mp_obj_t mod_trezorconfig_wipe(void) {
  storage_wipe();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_wipe_obj,
                                 mod_trezorconfig_wipe);

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezorconfig_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_check_pin),
     MP_ROM_PTR(&mod_trezorconfig_check_pin_obj)},
    {MP_ROM_QSTR(MP_QSTR_unlock), MP_ROM_PTR(&mod_trezorconfig_unlock_obj)},
    {MP_ROM_QSTR(MP_QSTR_lock), MP_ROM_PTR(&mod_trezorconfig_lock_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_unlocked),
     MP_ROM_PTR(&mod_trezorconfig_is_unlocked_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_pin), MP_ROM_PTR(&mod_trezorconfig_has_pin_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_pin_rem),
     MP_ROM_PTR(&mod_trezorconfig_get_pin_rem_obj)},
    {MP_ROM_QSTR(MP_QSTR_change_pin),
     MP_ROM_PTR(&mod_trezorconfig_change_pin_obj)},
    {MP_ROM_QSTR(MP_QSTR_ensure_not_wipe_code),
     MP_ROM_PTR(&mod_trezorconfig_ensure_not_wipe_code_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_wipe_code),
     MP_ROM_PTR(&mod_trezorconfig_has_wipe_code_obj)},
    {MP_ROM_QSTR(MP_QSTR_change_wipe_code),
     MP_ROM_PTR(&mod_trezorconfig_change_wipe_code_obj)},
    {MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezorconfig_get_obj)},
    {MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorconfig_set_obj)},
    {MP_ROM_QSTR(MP_QSTR_delete), MP_ROM_PTR(&mod_trezorconfig_delete_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_counter),
     MP_ROM_PTR(&mod_trezorconfig_set_counter_obj)},
    {MP_ROM_QSTR(MP_QSTR_next_counter),
     MP_ROM_PTR(&mod_trezorconfig_next_counter_obj)},
    {MP_ROM_QSTR(MP_QSTR_wipe), MP_ROM_PTR(&mod_trezorconfig_wipe_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals,
                            mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorconfig_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorconfig, mp_module_trezorconfig,
                   MICROPY_PY_TREZORCONFIG);

#endif  // MICROPY_PY_TREZORCONFIG
