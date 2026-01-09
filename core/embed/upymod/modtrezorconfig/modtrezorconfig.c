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

#include <trezor_rtl.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#if MICROPY_PY_TREZORCONFIG

#include <sec/storage.h>

#include "embed/upymod/trezorobj.h"

#include "memzero.h"

static secbool wrapped_ui_wait_callback(uint32_t wait, uint32_t progress,
                                        enum storage_ui_message_t message) {
  if (mp_obj_is_callable(MP_STATE_VM(trezorconfig_ui_wait_callback))) {
    mp_obj_t args[3] = {0};
    args[0] = mp_obj_new_int(wait);
    args[1] = mp_obj_new_int(progress);
    args[2] = mp_obj_new_int(message);
    if (mp_call_function_n_kw(MP_STATE_VM(trezorconfig_ui_wait_callback), 3, 0,
                              args) == mp_const_true) {
      return sectrue;
    }
  }
  return secfalse;
}

/// def init(
///    ui_wait_callback: Callable[[int, int, StorageMessage], bool] | None =
///    None
/// ) -> None:
///     """
///     Performs a soft re-initialization of the storage.
///     Locks the storage if it is currently unlocked, and allows setting
///     a new UI callback.
///     """
STATIC mp_obj_t mod_trezorconfig_init(size_t n_args, const mp_obj_t *args) {
  if (n_args > 0) {
    MP_STATE_VM(trezorconfig_ui_wait_callback) = args[0];
    storage_setup(wrapped_ui_wait_callback);
  } else {
    storage_setup(NULL);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_init_obj, 0, 1,
                                           mod_trezorconfig_init);

/// def unlock(pin: str, ext_salt: AnyBytes | None) -> bool:
///     """
///     Attempts to unlock the storage with the given PIN and external salt.
///     Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_unlock(mp_obj_t pin, mp_obj_t ext_salt) {
  mp_buffer_info_t pin_b = {0};
  mp_get_buffer_raise(pin, &pin_b, MP_BUFFER_READ);

  mp_buffer_info_t ext_salt_b = {0};
  ext_salt_b.buf = NULL;
  if (ext_salt != mp_const_none) {
    mp_get_buffer_raise(ext_salt, &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError,
                   MP_ERROR_TEXT("Invalid length of external salt."));
  }

  switch (storage_unlock(pin_b.buf, pin_b.len, ext_salt_b.buf)) {
    case UNLOCK_OK:
      return mp_const_true;
    case UNLOCK_NOT_INITIALIZED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Device is not initialized."));
    case UNLOCK_NO_PIN:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("No PIN is set."));
    case UNLOCK_PIN_GET_FAILS_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Failed to get PIN failure counter."));
    case UNLOCK_TOO_MANY_FAILS:
      mp_raise_msg(
          &mp_type_RuntimeError,
          MP_ERROR_TEXT("Too many incorrect PIN attempts; storage wiped."));
    case UNLOCK_UI_ISSUE:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("UI callback issue."));
    case UNLOCK_INCREASE_FAILS_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Failed to increase PIN failure counter."));
    case UNLOCK_INCORRECT_PIN:
      return mp_const_false;
    case UNLOCK_WRONG_STORAGE_VERSION:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Wrong storage version."));
    case UNLOCK_OPTIGA_HMAC_RESET_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("OPTIGA HMAC reset failed."));
    case UNLOCK_OPTIGA_COUNTER_RESET_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("OPTIGA counter reset failed."));
    case UNLOCK_TROPIC_RESET_MAC_AND_DESTROY_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Tropic MAC and destroy reset failed."));
    case UNLOCK_TROPIC_RESET_SLOTS_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Tropic slots reset failed."));
    case UNLOCK_PIN_RESET_FAILS_FAILED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Failed to reset PIN failure counter."));
    case UNLOCK_UNKNOWN:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Something went wrong during unlock."));
    default:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Something went wrong during unlock."));
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_unlock_obj,
                                 mod_trezorconfig_unlock);

/// def check_pin(pin: str, ext_salt: AnyBytes | None) -> bool:
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
///     newpin: str,
///     new_ext_salt: AnyBytes | None,
/// ) -> bool:
///     """
///     Change PIN and external salt. Returns True on success, False on failure.
///     Has to be run with unlocked storage.
///     """
STATIC mp_obj_t mod_trezorconfig_change_pin(size_t n_args,
                                            const mp_obj_t *args) {
  mp_buffer_info_t newpin = {0};
  mp_get_buffer_raise(args[0], &newpin, MP_BUFFER_READ);

  mp_buffer_info_t ext_salt_b = {0};
  const uint8_t *new_ext_salt = NULL;
  if (args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError,
                   MP_ERROR_TEXT("Invalid length of external salt."));
    new_ext_salt = ext_salt_b.buf;
  }

  switch (storage_change_pin(newpin.buf, newpin.len, new_ext_salt)) {
    case PIN_CHANGE_OK:
      return mp_const_true;
    case PIN_CHANGE_WIPE_CODE:
      return mp_const_false;
    case PIN_CHANGE_STORAGE_LOCKED:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Storage is locked."));
    case PIN_CHANGE_WRONG_ARGUMENT:
      mp_raise_msg(&mp_type_ValueError,
                   MP_ERROR_TEXT("Wrong argument provided."));
    case PIN_CHANGE_NOT_INITIALIZED:
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Device is not initialized."));
    case PIN_CHANGE_CANNOT_SET_PIN:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Cannot set the PIN."));
    case PIN_CHANGE_UNKNOWN:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Change PIN failed."));
    default:
      mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Change PIN failed."));
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_change_pin_obj, 2,
                                           2, mod_trezorconfig_change_pin);

/// def ensure_not_wipe_code(pin: str) -> None:
///     """
///     Wipes the device if the entered PIN is the wipe code.
///     """
STATIC mp_obj_t mod_trezorconfig_ensure_not_wipe_code(mp_obj_t pin) {
  mp_buffer_info_t pin_b = {0};
  mp_get_buffer_raise(pin, &pin_b, MP_BUFFER_READ);
  storage_ensure_not_wipe_code(pin_b.buf, pin_b.len);
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
///     pin: str,
///     ext_salt: AnyBytes | None,
///     wipe_code: str,
/// ) -> bool:
///     """
///     Change wipe code. Returns True on success, False on failure.
///     """
STATIC mp_obj_t mod_trezorconfig_change_wipe_code(size_t n_args,
                                                  const mp_obj_t *args) {
  mp_buffer_info_t pin_b = {0};
  mp_get_buffer_raise(args[0], &pin_b, MP_BUFFER_READ);

  mp_buffer_info_t wipe_code_b = {0};
  mp_get_buffer_raise(args[2], &wipe_code_b, MP_BUFFER_READ);

  mp_buffer_info_t ext_salt_b = {0};
  const uint8_t *ext_salt = NULL;
  if (args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &ext_salt_b, MP_BUFFER_READ);
    if (ext_salt_b.len != EXTERNAL_SALT_SIZE)
      mp_raise_msg(&mp_type_ValueError,
                   MP_ERROR_TEXT("Invalid length of external salt."));
    ext_salt = ext_salt_b.buf;
  }

  if (sectrue != storage_change_wipe_code(pin_b.buf, pin_b.len, ext_salt,
                                          wipe_code_b.buf, wipe_code_b.len)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorconfig_change_wipe_code_obj, 3, 3,
    mod_trezorconfig_change_wipe_code);

/// def get(app: int, key: int, public: bool = False) -> bytes | None:
///     """
///     Gets the value of the given key for the given app (or None if not set).
///     Raises a RuntimeError if decryption or authentication of the stored
///     value fails.
///     """
STATIC mp_obj_t mod_trezorconfig_get(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]);
  if (app == 0 || app > MAX_APPID) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid app ID."));
  }
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
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get value from storage."));
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_get_obj, 2, 3,
                                           mod_trezorconfig_get);

/// def set(app: int, key: int, value: AnyBytes, public: bool = False) -> None:
///     """
///     Sets a value of given key for given app.
///     """
STATIC mp_obj_t mod_trezorconfig_set(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]);
  if (app == 0 || app > MAX_APPID) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid app ID."));
  }
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 3 && args[3] == mp_const_true) {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  mp_buffer_info_t value;
  mp_get_buffer_raise(args[2], &value, MP_BUFFER_READ);
  if (value.len > UINT16_MAX ||
      sectrue != storage_set(appkey, value.buf, value.len)) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Could not save value"));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_set_obj, 3, 4,
                                           mod_trezorconfig_set);

/// def delete(
///     app: int, key: int, public: bool = False, writable_locked: bool = False
/// ) -> bool:
///     """
///     Deletes the given key of the given app.
///     """
STATIC mp_obj_t mod_trezorconfig_delete(size_t n_args, const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]);
  if (app == 0 || app > MAX_APPID) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid app ID."));
  }
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 2 && args[2] == mp_const_true) {
    app |= FLAG_PUBLIC;
  }
  if (n_args > 3 && args[3] == mp_const_true) {
    app |= FLAGS_WRITE;
    if (args[2] != mp_const_true) {
      mp_raise_msg(&mp_type_ValueError,
                   MP_ERROR_TEXT("Writable entry must be public."));
    }
  }
  uint16_t appkey = (app << 8) | key;
  if (sectrue != storage_delete(appkey)) {
    return mp_const_false;
  }
  return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_delete_obj, 2, 4,
                                           mod_trezorconfig_delete);

/// def set_counter(
///     app: int, key: int, count: int, writable_locked: bool = False
/// ) -> None:
///     """
///     Sets the given key of the given app as a counter with the given value.
///     """
STATIC mp_obj_t mod_trezorconfig_set_counter(size_t n_args,
                                             const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]);
  if (app == 0 || app > MAX_APPID) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid app ID."));
  }
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 3 && args[3] == mp_const_true) {
    app |= FLAGS_WRITE;
  } else {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  mp_uint_t count = trezor_obj_get_uint(args[2]);
  if (count > UINT32_MAX || sectrue != storage_set_counter(appkey, count)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to set value in storage."));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_set_counter_obj, 3,
                                           4, mod_trezorconfig_set_counter);

/// def next_counter(
///    app: int, key: int, writable_locked: bool = False,
/// ) -> int:
///     """
///     Increments the counter stored under the given key of the given app and
///     returns the new value.
///     """
STATIC mp_obj_t mod_trezorconfig_next_counter(size_t n_args,
                                              const mp_obj_t *args) {
  uint8_t app = trezor_obj_get_uint8(args[0]);
  if (app == 0 || app > MAX_APPID) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid app ID."));
  }
  uint8_t key = trezor_obj_get_uint8(args[1]);
  if (n_args > 2 && args[2] == mp_const_true) {
    app |= FLAGS_WRITE;
  } else {
    app |= FLAG_PUBLIC;
  }
  uint16_t appkey = (app << 8) | key;
  uint32_t count = 0;
  if (sectrue != storage_next_counter(appkey, &count)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to set value in storage."));
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

/// from enum import IntEnum
/// class StorageMessage(IntEnum):
///     NO_MSG = 0
///     VERIFYING_PIN_MSG = 1
///     PROCESSING_MSG = 2
///     STARTING_MSG = 3
///     WRONG_PIN_MSG = 4
STATIC const qstr mod_trezorconfig_StorageMessage_fields[] = {
    MP_QSTR_NO_MSG, MP_QSTR_VERIFYING_PIN_MSG, MP_QSTR_PROCESSING_MSG,
    MP_QSTR_STARTING_MSG, MP_QSTR_WRONG_PIN_MSG};
STATIC MP_DEFINE_ATTRTUPLE(
    mod_trezorconfig_StorageMessage_obj, mod_trezorconfig_StorageMessage_fields,
    (sizeof(mod_trezorconfig_StorageMessage_fields) / sizeof(qstr)),
    MP_ROM_INT(0), MP_ROM_INT(1), MP_ROM_INT(2), MP_ROM_INT(3), MP_ROM_INT(4));

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
    {MP_ROM_QSTR(MP_QSTR_StorageMessage),
     MP_ROM_PTR(&mod_trezorconfig_StorageMessage_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals,
                            mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorconfig_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorconfig, mp_module_trezorconfig);

#endif  // MICROPY_PY_TREZORCONFIG
