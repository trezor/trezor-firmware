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

#include <io/app_arena.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#include "../trezorobj.h"

#include "modtrezorapp-image.h"

/// package: trezorapp

/// def create_image() -> AppImage:
///     """
///     Creates a new empty application image. The returned handle
///     can be used to load the image content and run it.
///     """
STATIC mp_obj_t mod_trezorapp_create_image(void) {
  app_image_handle_t handle = APP_IMAGE_HANDLE_INVALID;
  ts_t status = app_arena_create_image(&handle);
  if (ts_eq(status, TS_ENOMEM)) {
    mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Not enough memory"));
  }
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to create app image"));
  }

  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->handle = handle;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_create_image_obj,
                                 mod_trezorapp_create_image);

/// def get_image_by_index(idx: int) -> AppImage | None:
///     """
///     Returns the app image at the specified index in the app arena list.
///     """
STATIC mp_obj_t mod_trezorapp_arena_get_image_by_index(mp_obj_t idx_obj) {
  size_t idx = mp_obj_get_int(idx_obj);

  app_image_handle_t handle = APP_IMAGE_HANDLE_INVALID;
  ts_t status = app_arena_get_image_by_index(idx, &handle);
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get app image"));
  }

  if (handle != APP_IMAGE_HANDLE_INVALID) {
    mp_obj_AppImage_t *o =
        mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
    o->handle = handle;
    return MP_OBJ_FROM_PTR(o);
  } else {
    return mp_const_none;
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_arena_get_image_by_index_obj,
                                 mod_trezorapp_arena_get_image_by_index);

/// def get_image_by_handle(handle: int) -> AppImage:
///     """
///     Returns the application image with the specified handle.
///     """
STATIC mp_obj_t mod_trezorapp_arena_get_image_by_handle(mp_obj_t handle_obj) {
  app_image_handle_t handle = mp_obj_get_int(handle_obj);

  app_image_info_t info;
  ts_t status = app_image_get_info(handle, &info);
  if (ts_eq(status, TS_ENOENT)) {
    mp_raise_ValueError(MP_ERROR_TEXT("App image not found"));
  } else if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get app image by handle"));
  }

  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->handle = handle;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_arena_get_image_by_handle_obj,
                                 mod_trezorapp_arena_get_image_by_handle);

/// def clear_event() -> None:
///     """
///     Clears the pending event on the app arena, if any.
///     """
STATIC mp_obj_t mod_trezorapp_arena_clear_event(void) {
  ts_t status = app_arena_clear_event();
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to clear app arena event"));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_clear_event_obj,
                                 mod_trezorapp_arena_clear_event);

/// def get_image_count() -> int:
///     """
///     Returns the number of application images currently
///     loaded in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_get_image_count(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get app arena info"));
  }

  return mp_obj_new_int(info.image_count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_get_image_count_obj,
                                 mod_trezorapp_arena_get_image_count);

/// def get_mem_total() -> int:
///     """
///     Returns the total memory available in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_get_mem_total(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get app arena info"));
  }

  return mp_obj_new_int(info.total_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_get_mem_total_obj,
                                 mod_trezorapp_arena_get_mem_total);

/// def get_mem_free() -> int:
///     """
///     Returns the free memory available in the app arena.
///     """
STATIC mp_obj_t mod_trezorapp_arena_get_mem_free(void) {
  app_arena_info_t info;
  ts_t status = app_arena_get_info(&info);
  if (ts_error(status)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get app arena info"));
  }

  return mp_obj_new_int(info.free_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorapp_arena_get_mem_free_obj,
                                 mod_trezorapp_arena_get_mem_free);

STATIC const mp_rom_map_elem_t mod_module_trezorapp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorapp)},
    {MP_ROM_QSTR(MP_QSTR_create_image),
     MP_ROM_PTR(&mod_trezorapp_create_image_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_image_by_index),
     MP_ROM_PTR(&mod_trezorapp_arena_get_image_by_index_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_image_count),
     MP_ROM_PTR(&mod_trezorapp_arena_get_image_count_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_image_by_handle),
     MP_ROM_PTR(&mod_trezorapp_arena_get_image_by_handle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_event),
     MP_ROM_PTR(&mod_trezorapp_arena_clear_event_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_mem_total),
     MP_ROM_PTR(&mod_trezorapp_arena_get_mem_total_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_mem_free),
     MP_ROM_PTR(&mod_trezorapp_arena_get_mem_free_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorapp_globals,
                            mod_module_trezorapp_globals_table);

const mp_obj_module_t mp_module_trezorapp = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorapp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorapp, mp_module_trezorapp);
