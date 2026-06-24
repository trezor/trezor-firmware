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

#ifdef USE_APP_LOADING

#include <trezor_rtl.h>

#include <io/app_arena.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#include "../trezorobj.h"

#include "modtrezorapp-image.h"

/// package: trezorapp

/// def create_image(header: AnyBytes, proof: AnyBytes) -> AppImage:
///     """
///     Create a new application image from header and proof.
///     The returned handle can be used to load the rest of the
///     image content and run it.
///     """
STATIC mp_obj_t mod_trezorapp_create_image(mp_obj_t header_obj,
                                           mp_obj_t proof_obj) {
  app_image_handle_t handle = APP_IMAGE_HANDLE_INVALID;

  mp_buffer_info_t header_buf;
  mp_get_buffer_raise(header_obj, &header_buf, MP_BUFFER_READ);

  mp_buffer_info_t proof_buf;
  mp_get_buffer_raise(proof_obj, &proof_buf, MP_BUFFER_READ);

  if (proof_buf.len % sizeof(sha256_digest_t) != 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid Merkle proof length"));
  }

  ts_t status =
      app_arena_create_image(header_buf.buf, header_buf.len, proof_buf.buf,
                             proof_buf.len / sizeof(sha256_digest_t), &handle);

  if (ts_eq(status, TS_ENOMEM)) {
    mp_raise_type(&mp_type_AppImageMemoryError);
  } else if (ts_eq(status, TS_EBADMSG)) {
    mp_raise_type(&mp_type_AppImageVerificationError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }

  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->handle = handle;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorapp_create_image_obj,
                                 mod_trezorapp_create_image);

typedef struct {
  mp_obj_base_t base;
  size_t idx;
} mp_obj_AppImageIter_t;

STATIC mp_obj_t mod_trezorapp_images_iternext(mp_obj_t self_in) {
  mp_obj_AppImageIter_t *self = MP_OBJ_TO_PTR(self_in);

  app_image_handle_t handle = APP_IMAGE_HANDLE_INVALID;
  ts_t status = app_arena_get_image_by_index(self->idx, &handle);
  if (ts_error(status)) {
    mp_raise_type(&mp_type_AppArenaError);
  }

  if (handle == APP_IMAGE_HANDLE_INVALID) {
    return MP_OBJ_STOP_ITERATION;
  }

  self->idx++;
  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->handle = handle;
  return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_obj_type_t mod_trezorapp_AppImageIter_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppImageIter,
    .getiter = mp_identity_getiter,
    .iternext = mod_trezorapp_images_iternext,
};

/// def images() -> Iterator[AppImage]:
///     """
///     Return an iterator over all app images in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_images(void) {
  mp_obj_AppImageIter_t *o =
      mp_obj_malloc(mp_obj_AppImageIter_t, &mod_trezorapp_AppImageIter_type);
  o->idx = 0;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_images_obj,
                                 mod_trezorapp_images);

/// def image_by_handle(handle: int) -> AppImage:
///     """
///     Return the application image with the specified handle.
///     """
STATIC mp_obj_t mod_trezorapp_arena_image_by_handle(mp_obj_t handle_obj) {
  app_image_handle_t handle = mp_obj_get_int(handle_obj);

  app_image_info_t info;
  ts_t status = app_image_get_info(handle, &info);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_type(&mp_type_AppImageNotFoundError);
  } else if (ts_error(status)) {
    mp_raise_type(&mp_type_AppImageError);
  }

  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->handle = handle;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_arena_image_by_handle_obj,
                                 mod_trezorapp_arena_image_by_handle);

/// def clear_event() -> None:
///     """
///     Clear the pending event on the app arena, if any.
///     """
STATIC mp_obj_t mod_trezorapp_arena_clear_event(void) {
  ts_t status = app_arena_clear_event();
  if (ts_error(status)) {
    mp_raise_type(&mp_type_AppArenaError);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_clear_event_obj,
                                 mod_trezorapp_arena_clear_event);

/// def image_count() -> int:
///     """
///     Return the number of application images currently
///     loaded in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_image_count(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_type(&mp_type_AppArenaError);
  }

  return mp_obj_new_int(info.image_count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_image_count_obj,
                                 mod_trezorapp_arena_image_count);

/// def mem_total() -> int:
///     """
///     Return the total memory available in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_mem_total(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_type(&mp_type_AppArenaError);
  }

  return mp_obj_new_int(info.total_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_mem_total_obj,
                                 mod_trezorapp_arena_mem_total);

/// def mem_free() -> int:
///     """
///     Return the free memory available in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_mem_free(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_type(&mp_type_AppArenaError);
  }

  return mp_obj_new_int(info.free_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_mem_free_obj,
                                 mod_trezorapp_arena_mem_free);

STATIC const mp_rom_map_elem_t mod_module_trezorapp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorapp)},
    {MP_ROM_QSTR(MP_QSTR_AppError), MP_ROM_PTR(&mp_type_AppError)},
    {MP_ROM_QSTR(MP_QSTR_AppImageError), MP_ROM_PTR(&mp_type_AppImageError)},
    {MP_ROM_QSTR(MP_QSTR_AppImageNotFoundError),
     MP_ROM_PTR(&mp_type_AppImageNotFoundError)},
    {MP_ROM_QSTR(MP_QSTR_AppImageMemoryError),
     MP_ROM_PTR(&mp_type_AppImageMemoryError)},
    {MP_ROM_QSTR(MP_QSTR_AppImageVerificationError),
     MP_ROM_PTR(&mp_type_AppImageVerificationError)},
    {MP_ROM_QSTR(MP_QSTR_AppArenaError), MP_ROM_PTR(&mp_type_AppArenaError)},
    {MP_ROM_QSTR(MP_QSTR_create_image),
     MP_ROM_PTR(&mod_trezorapp_create_image_obj)},
    {MP_ROM_QSTR(MP_QSTR_images), MP_ROM_PTR(&mod_trezorapp_images_obj)},
    {MP_ROM_QSTR(MP_QSTR_image_count),
     MP_ROM_PTR(&mod_trezorapp_arena_image_count_obj)},
    {MP_ROM_QSTR(MP_QSTR_image_by_handle),
     MP_ROM_PTR(&mod_trezorapp_arena_image_by_handle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_event),
     MP_ROM_PTR(&mod_trezorapp_arena_clear_event_obj)},
    {MP_ROM_QSTR(MP_QSTR_mem_total),
     MP_ROM_PTR(&mod_trezorapp_arena_mem_total_obj)},
    {MP_ROM_QSTR(MP_QSTR_mem_free),
     MP_ROM_PTR(&mod_trezorapp_arena_mem_free_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorapp_globals,
                            mod_module_trezorapp_globals_table);

const mp_obj_module_t mp_module_trezorapp = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorapp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorapp, mp_module_trezorapp);

#endif  // USE_APP_LOADING
