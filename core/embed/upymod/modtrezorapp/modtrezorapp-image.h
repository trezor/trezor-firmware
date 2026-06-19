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

#include <py/obj.h>
#include <py/runtime.h>

#include <trezor_rtl.h>

#include <io/app_arena.h>

/// package: trezorapp

/// class AppImage:
///     """
///     Third-party application loaded or running in the app arena,
///     a RAM region reserved for application images.
///     """
typedef struct _mp_obj_AppImage_t {
  mp_obj_base_t base;
  app_image_handle_t handle;
} mp_obj_AppImage_t;

/// def get_handle(self) -> int
///     """
///     Returns the image internal unique handle.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_get_handle(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int(o->handle);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_get_handle_obj,
                                 mod_trezorapp_AppImage_get_handle);

/// def get_task_id(self) -> int:
///     """
///     Gets the task ID associated with the application image.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_get_task_id(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  if (info.state != APP_IMAGE_STATE_RUNNING || info.task_id == 0) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("AppImage is not running."));
  }

  return mp_obj_new_int(info.task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_get_task_id_obj,
                                 mod_trezorapp_AppImage_get_task_id);

/// def is_running(self) -> bool:
///     """
///     Checks if the application image is currently running.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_is_running(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  return mp_obj_new_bool(info.state == APP_IMAGE_STATE_RUNNING);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_is_running_obj,
                                 mod_trezorapp_AppImage_is_running);

/// def is_verified(self) -> bool:
///     """
///     Checks if the application image has been verified.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_is_verified(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  return mp_obj_new_bool(info.state == APP_IMAGE_STATE_VERIFIED ||
                         info.state == APP_IMAGE_STATE_RUNNING);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_is_verified_obj,
                                 mod_trezorapp_AppImage_is_verified);

/// def get_id(self) -> str:
///     """
///     Returns the ID of the application image.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_get_id(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  return mp_obj_new_str(info.id, strlen(info.id));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_get_id_obj,
                                 mod_trezorapp_AppImage_get_id);

/// def get_version(self) -> tuple[int, int]:
///     """
///     Returns the version of the application image as a tuple (major, minor).
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_get_version(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  mp_obj_t version_tuple[2];
  version_tuple[0] = mp_obj_new_int((info.version >> 24) & 0xFF);  // major
  version_tuple[1] = mp_obj_new_int((info.version >> 16) & 0xFF);  // minor

  return mp_obj_new_tuple(2, version_tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_get_version_obj,
                                 mod_trezorapp_AppImage_get_version);

/// def get_hash(self) -> bytes:
///     """
///     Returns the hash of the application image.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_get_hash(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  ts_t status = app_image_get_info(o->handle, &info);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get AppImage info."));
  }

  const char dummy_hash[32] = {0};  // TODO: Replace with actual hash retrieval
  return mp_obj_new_bytes((const byte *)dummy_hash, sizeof(dummy_hash));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_get_hash_obj,
                                 mod_trezorapp_AppImage_get_hash);

/// def write_chunk(self, data: AnyBytes) -> None:
///     """
///     Writes a chunk of image data into app-arena memory.
///     Allowed only while the image is in the loading state.
///     Call verify() after all chunks are written.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_write_chunk(mp_obj_t self,
                                                   mp_obj_t data_obj) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

  ts_t status = app_image_write_chunk(o->handle, bufinfo.buf, bufinfo.len);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_eq(status, TS_ENOMEM)) {
    mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Not enough memory"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to write to AppImage."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorapp_AppImage_write_chunk_obj,
                                 mod_trezorapp_AppImage_write_chunk);

/// def verify(self, merkle_proof: AnyBytes) -> None:
///     """
///     Validates image integrity and verifies its signature.
///     If verification succeeds, the image transitions to the
///     verified state.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_verify(mp_obj_t self,
                                              mp_obj_t merkle_proof_obj) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(merkle_proof_obj, &bufinfo, MP_BUFFER_READ);

  ts_t status = app_image_verify(o->handle, bufinfo.buf, bufinfo.len);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_eq(status, TS_ENOMEM)) {
    mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Not enough memory"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to verify AppImage."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorapp_AppImage_verify_obj,
                                 mod_trezorapp_AppImage_verify);

/// def delete(self) -> None:
///     """
///     Deletes the application and releases its resources.
///     If the image is currently running, it is stopped before
///     deletion. After deletion, the AppImage object is invalid
///     and must not be used.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_delete(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  ts_t status = app_image_delete(o->handle);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to delete AppImage."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_delete_obj,
                                 mod_trezorapp_AppImage_delete);

/// def run(self) -> int:
///     """
///     Runs the loaded application image. Only verified images
///     are runnable. If the image is already running,
///     this operation has no effect.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_run(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  systask_id_t task_id = 0;
  ts_t status = app_image_run(o->handle, &task_id);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to run app image."));
  }

  return mp_obj_new_int(task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_run_obj,
                                 mod_trezorapp_AppImage_run);

/// def stop(self) -> None:
///     """
///     Stops the running application image. If the image is not running,
///     this operation has no effect.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_stop(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  ts_t status = app_image_stop(o->handle);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid AppImage handle"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to stop AppImage."));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_stop_obj,
                                 mod_trezorapp_AppImage_stop);

STATIC const mp_rom_map_elem_t mod_trezorapp_AppImage_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_handle),
     MP_ROM_PTR(&mod_trezorapp_AppImage_get_handle_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_task_id),
     MP_ROM_PTR(&mod_trezorapp_AppImage_get_task_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_running),
     MP_ROM_PTR(&mod_trezorapp_AppImage_is_running_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_verified),
     MP_ROM_PTR(&mod_trezorapp_AppImage_is_verified_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_id),
     MP_ROM_PTR(&mod_trezorapp_AppImage_get_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_version),
     MP_ROM_PTR(&mod_trezorapp_AppImage_get_version_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_hash),
     MP_ROM_PTR(&mod_trezorapp_AppImage_get_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_write_chunk),
     MP_ROM_PTR(&mod_trezorapp_AppImage_write_chunk_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify),
     MP_ROM_PTR(&mod_trezorapp_AppImage_verify_obj)},
    {MP_ROM_QSTR(MP_QSTR_delete),
     MP_ROM_PTR(&mod_trezorapp_AppImage_delete_obj)},
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&mod_trezorapp_AppImage_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&mod_trezorapp_AppImage_stop_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorapp_AppImage_locals_dict,
                            mod_trezorapp_AppImage_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorapp_AppImage_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppImage,
    .locals_dict = (void *)&mod_trezorapp_AppImage_locals_dict,
};
