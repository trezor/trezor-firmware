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

/// class AppError(Exception):
///     """
///     Base exception for all trezorapp errors.
///     """
MP_DEFINE_EXCEPTION(AppError, Exception)

/// class AppImageError(AppError):
///     """
///     Base exception for app image errors.
///     """
MP_DEFINE_EXCEPTION(AppImageError, AppError)

/// class AppImageNotFoundError(AppImageError):
///     """
///     Raised when the AppImage handle is invalid or the image no longer
///     exists.
///     """
MP_DEFINE_EXCEPTION(AppImageNotFoundError, AppImageError)

/// class AppImageMemoryError(AppImageError):
///     """
///     Raised when there is not enough memory in the app arena.
///     """
MP_DEFINE_EXCEPTION(AppImageMemoryError, AppImageError)

/// class AppImageVerificationError(AppImageError):
///     """
///     Raised when the app image data fails verification.
///     """
MP_DEFINE_EXCEPTION(AppImageVerificationError, AppImageError)

/// class AppArenaError(AppError):
///     """
///     Raised when an app arena operation fails.
///     """
MP_DEFINE_EXCEPTION(AppArenaError, AppError)

/// class AppImage:
///     """
///     External application loaded in the app arena
///     """
typedef struct _mp_obj_AppImage_t {
  mp_obj_base_t base;
  app_image_handle_t handle;
} mp_obj_AppImage_t;

STATIC void app_image_get_info_or_raise(app_image_handle_t handle,
                                        app_image_info_t *info) {
  ts_t status = app_image_get_info(handle, info);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }
}

/// def handle(self) -> int:
///     """
///     Return the image internal unique handle.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_handle(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int(o->handle);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_handle_obj,
                                 mod_trezorapp_AppImage_handle);

/// def task_id(self) -> int:
///     """
///     Return the task ID associated with the application image.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_task_id(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  if (!info.running) {
    mp_raise_type(&mp_type_AppImageError);
  }

  return mp_obj_new_int(info.task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_task_id_obj,
                                 mod_trezorapp_AppImage_task_id);

/// def is_running(self) -> bool:
///     """
///     Check if the application image is currently running.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_is_running(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_bool(info.running);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_is_running_obj,
                                 mod_trezorapp_AppImage_is_running);

/// def is_ready(self) -> bool:
///     """
///     Check if the application image has been fully loaded and verified.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_is_ready(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_bool(info.ready);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_is_ready_obj,
                                 mod_trezorapp_AppImage_is_ready);

/// def id(self) -> str:
///     """
///     Return the ID of the application image.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_id(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_str(info.id, strnlen(info.id, sizeof(info.id)));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_id_obj,
                                 mod_trezorapp_AppImage_id);

/// def size(self) -> int:
///     """
///     Return the size of the application image in bytes.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_size(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_int(info.code_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_size_obj,
                                 mod_trezorapp_AppImage_size);

/// def chunk_size(self) -> int:
///     """
///     Return the expected size of each payload chunk in bytes.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_chunk_size(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_int(info.chunk_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_chunk_size_obj,
                                 mod_trezorapp_AppImage_chunk_size);

/// def version(self) -> tuple[int, int, int, int]:
///     """
///     Return the version of the application image as a tuple (major, minor,
///     patch, build).
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_version(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  mp_obj_t version_tuple[4];
  version_tuple[0] = mp_obj_new_int((info.version >> 0) & 0xFF);   // major
  version_tuple[1] = mp_obj_new_int((info.version >> 8) & 0xFF);   // minor
  version_tuple[2] = mp_obj_new_int((info.version >> 16) & 0xFF);  // patch
  version_tuple[3] = mp_obj_new_int((info.version >> 24) & 0xFF);  // build

  return mp_obj_new_tuple(4, version_tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_version_obj,
                                 mod_trezorapp_AppImage_version);

/// def name(self) -> str:
///     """
///     Return the name of the application.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_name(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_str(info.name, strnlen(info.name, sizeof(info.name)));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_name_obj,
                                 mod_trezorapp_AppImage_name);

/// def vendor(self) -> str:
///     """
///     Return the vendor of the application.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_vendor(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_str(info.vendor, strnlen(info.vendor, sizeof(info.vendor)));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_vendor_obj,
                                 mod_trezorapp_AppImage_vendor);

/// def ring(self) -> int:
///     """
///     Return the privilege ring of the application.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_ring(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_int(info.ring);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_ring_obj,
                                 mod_trezorapp_AppImage_ring);

/// def header_hash(self) -> bytes:
///     """
///     Return the hash of the application image header.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_header_hash(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  app_image_info_t info;
  app_image_get_info_or_raise(o->handle, &info);

  return mp_obj_new_bytes((const byte *)&info.header_hash,
                          sizeof(info.header_hash));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_header_hash_obj,
                                 mod_trezorapp_AppImage_header_hash);

/// def write_chunk(self, data: AnyBytes, hash: AnyBytes) -> None:
///     """
///     Write a chunk of image data into app-arena memory.
///     Allowed only while the image is in the loading state.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_write_chunk(mp_obj_t self,
                                                   mp_obj_t data_obj,
                                                   mp_obj_t hash_obj) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  mp_buffer_info_t data = {0};
  mp_get_buffer_raise(data_obj, &data, MP_BUFFER_READ);

  mp_buffer_info_t hash = {0};
  mp_get_buffer_raise(hash_obj, &hash, MP_BUFFER_READ);
  if (hash.len != sizeof(sha256_digest_t)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Hash must be 32 bytes"));
  }

  ts_t status = app_image_write_chunk(o->handle, data.buf, data.len,
                                      (const sha256_digest_t *)hash.buf);

  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_eq(status, TS_ENOMEM)) {
    mp_raise_type(&mp_type_AppImageMemoryError);
  } else if (ts_eq(status, TS_EBADMSG)) {
    mp_raise_type(&mp_type_AppImageVerificationError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorapp_AppImage_write_chunk_obj,
                                 mod_trezorapp_AppImage_write_chunk);

/// def delete(self) -> None:
///     """
///     Delete the application and release its resources.
///     If the image is currently running, it is stopped before
///     deletion. After deletion, the AppImage object is invalid
///     and must not be used.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_delete(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  ts_t status = app_image_delete(o->handle);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_delete_obj,
                                 mod_trezorapp_AppImage_delete);

/// def run(self) -> int:
///     """
///     Run the loaded application image and return its task ID.
///     If the image is already running, the function returns its task ID.
///     Only ready images are runnable.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_run(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  systask_id_t task_id = 0;
  ts_t status = app_image_run(o->handle, &task_id);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }

  return mp_obj_new_int(task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_run_obj,
                                 mod_trezorapp_AppImage_run);

/// def stop(self) -> None:
///     """
///     Stop the running application image. If the image is not running,
///     this operation has no effect.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_stop(mp_obj_t self) {
  mp_obj_AppImage_t *o = MP_OBJ_TO_PTR(self);

  ts_t status = app_image_stop(o->handle);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppImage_stop_obj,
                                 mod_trezorapp_AppImage_stop);

typedef struct {
  mp_obj_base_t base;
  // Handle of the AppImage being iterated over
  app_image_handle_t handle;
  // Offset in the curves array of the next curve to return
  size_t offset;
} mp_obj_AppCurveIter_t;

STATIC mp_obj_t mod_trezorapp_AppCurveIter_iternext(mp_obj_t self_in) {
  mp_obj_AppCurveIter_t *self = MP_OBJ_TO_PTR(self_in);

  app_image_info_t info;
  app_image_get_info_or_raise(self->handle, &info);

  size_t offset = self->offset;
  if (offset >= APP_HEADER_CURVES_MAX_LEN) {
    return MP_OBJ_STOP_ITERATION;
  }

  size_t len = strnlen(info.curves + offset, sizeof(info.curves) - offset);
  if (len == 0) {
    return MP_OBJ_STOP_ITERATION;
  }

  self->offset = MIN(offset + len + 1, APP_HEADER_CURVES_MAX_LEN);

  return mp_obj_new_str(info.curves + offset, len);
}

STATIC const mp_obj_type_t mod_trezorapp_AppCurveIter_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppCurveIter,
    .getiter = mp_identity_getiter,
    .iternext = mod_trezorapp_AppCurveIter_iternext,
};

/// def allowed_curves() -> Iterator[str]:
///     """
///     Return an iterator over the allowed curves
///     """
STATIC mp_obj_t mod_trezorapp_allowed_curves(mp_obj_t self) {
  mp_obj_AppImage_t *image = MP_OBJ_TO_PTR(self);

  mp_obj_AppCurveIter_t *o =
      mp_obj_malloc(mp_obj_AppCurveIter_t, &mod_trezorapp_AppCurveIter_type);
  o->handle = image->handle;
  o->offset = 0;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_allowed_curves_obj,
                                 mod_trezorapp_allowed_curves);


typedef struct {
  mp_obj_base_t base;
  // Handle of the AppImage being iterated over
  app_image_handle_t handle;
  // Offset in the paths array of the next path to return
  size_t offset;
} mp_obj_AppPathIter_t;

STATIC mp_obj_t mod_trezorapp_AppPathIter_iternext(mp_obj_t self_in) {
  mp_obj_AppPathIter_t *self = MP_OBJ_TO_PTR(self_in);

  app_image_info_t info;
  app_image_get_info_or_raise(self->handle, &info);

  size_t offset = self->offset;
  if (offset >= APP_HEADER_PATHS_MAX_LEN) {
    return MP_OBJ_STOP_ITERATION;
  }

  size_t len = strnlen(info.paths + offset, sizeof(info.paths) - offset);
  if (len == 0) {
    return MP_OBJ_STOP_ITERATION;
  }

  self->offset = MIN(offset + len + 1, APP_HEADER_PATHS_MAX_LEN);

  return mp_obj_new_str(info.paths + offset, len);
}

STATIC const mp_obj_type_t mod_trezorapp_AppPathIter_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppPathIter,
    .getiter = mp_identity_getiter,
    .iternext = mod_trezorapp_AppPathIter_iternext,
};

/// def allowed_paths() -> Iterator[str]:
///     """
///     Return an iterator over the allowed BIP32 path prefixes.
///     """
STATIC mp_obj_t mod_trezorapp_allowed_paths(mp_obj_t self) {
  mp_obj_AppImage_t *image = MP_OBJ_TO_PTR(self);

  mp_obj_AppPathIter_t *o =
      mp_obj_malloc(mp_obj_AppPathIter_t, &mod_trezorapp_AppPathIter_type);
  o->handle = image->handle;
  o->offset = 0;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_allowed_paths_obj,
                                 mod_trezorapp_allowed_paths);

STATIC const mp_rom_map_elem_t mod_trezorapp_AppImage_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_handle),
     MP_ROM_PTR(&mod_trezorapp_AppImage_handle_obj)},
    {MP_ROM_QSTR(MP_QSTR_task_id),
     MP_ROM_PTR(&mod_trezorapp_AppImage_task_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_running),
     MP_ROM_PTR(&mod_trezorapp_AppImage_is_running_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_ready),
     MP_ROM_PTR(&mod_trezorapp_AppImage_is_ready_obj)},
    {MP_ROM_QSTR(MP_QSTR_id), MP_ROM_PTR(&mod_trezorapp_AppImage_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&mod_trezorapp_AppImage_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_chunk_size),
     MP_ROM_PTR(&mod_trezorapp_AppImage_chunk_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_version),
     MP_ROM_PTR(&mod_trezorapp_AppImage_version_obj)},
    {MP_ROM_QSTR(MP_QSTR_name), MP_ROM_PTR(&mod_trezorapp_AppImage_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_vendor),
     MP_ROM_PTR(&mod_trezorapp_AppImage_vendor_obj)},
    {MP_ROM_QSTR(MP_QSTR_ring), MP_ROM_PTR(&mod_trezorapp_AppImage_ring_obj)},
    {MP_ROM_QSTR(MP_QSTR_header_hash),
     MP_ROM_PTR(&mod_trezorapp_AppImage_header_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_write_chunk),
     MP_ROM_PTR(&mod_trezorapp_AppImage_write_chunk_obj)},
    {MP_ROM_QSTR(MP_QSTR_delete),
     MP_ROM_PTR(&mod_trezorapp_AppImage_delete_obj)},
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&mod_trezorapp_AppImage_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&mod_trezorapp_AppImage_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR_allowed_curves),
     MP_ROM_PTR(&mod_trezorapp_allowed_curves_obj)},
    {MP_ROM_QSTR(MP_QSTR_allowed_paths),
     MP_ROM_PTR(&mod_trezorapp_allowed_paths_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorapp_AppImage_locals_dict,
                            mod_trezorapp_AppImage_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorapp_AppImage_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppImage,
    .locals_dict = (void *)&mod_trezorapp_AppImage_locals_dict,
};
