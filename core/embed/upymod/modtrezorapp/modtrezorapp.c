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

#include <unistd.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#if MICROPY_PY_TREZORAPP

#include <util/app_cache.h>
#include <util/app_loader.h>

#include "embed/upymod/trezorobj.h"

#include "modtrezorapp-image.h"
#include "modtrezorapp-task.h"

/// package: trezorapp

/// def spawn_task(app_hash: AnyBytes) -> AppTask:
///     """
///     Spawns an application task from the app cache.
///     """
STATIC mp_obj_t mod_trezorapp_spawn_task(mp_obj_t app_hash_obj) {
  mp_buffer_info_t hash = {0};
  mp_get_buffer_raise(app_hash_obj, &hash, MP_BUFFER_READ);

  if (hash.len != sizeof(app_hash_t)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid app hash size"));
  }

  const app_hash_t *hash_ptr = (const app_hash_t *)hash.buf;

  systask_id_t task_id;
  if (!app_task_spawn(hash_ptr, &task_id)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to spawn app from app cache"));
  }

  mp_obj_AppTask_t *o =
      mp_obj_malloc(mp_obj_AppTask_t, &mod_trezorapp_AppTask_type);
  o->task_id = task_id;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_spawn_task_obj,
                                 mod_trezorapp_spawn_task);

/// def create_image(app_hash: AnyBytes, size: int) -> AppImage:
///     """
///     Creates a new application image in the app cache.
///     """
STATIC mp_obj_t mod_trezorapp_create_image(mp_obj_t app_hash_obj,
                                           mp_obj_t size_obj) {
  mp_buffer_info_t hash = {0};
  mp_get_buffer_raise(app_hash_obj, &hash, MP_BUFFER_READ);

  if (hash.len != sizeof(app_hash_t)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid app hash size"));
  }

  const app_hash_t *hash_ptr = (const app_hash_t *)hash.buf;

  size_t size = mp_obj_get_int(size_obj);

  app_cache_image_t *image = app_cache_create_image(hash_ptr, size);

  if (image == NULL) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to create app image in app cache"));
  }
  mp_obj_AppImage_t *o =
      mp_obj_malloc(mp_obj_AppImage_t, &mod_trezorapp_AppImage_type);
  o->image = image;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorapp_create_image_obj,
                                 mod_trezorapp_create_image);

STATIC const mp_rom_map_elem_t mp_module_trezorapp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorapp)},

    {MP_ROM_QSTR(MP_QSTR_spawn_task),
     MP_ROM_PTR(&mod_trezorapp_spawn_task_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_image),
     MP_ROM_PTR(&mod_trezorapp_create_image_obj)},
    {MP_ROM_QSTR(MP_QSTR_AppTask), MP_ROM_PTR(&mod_trezorapp_AppTask_type)},
    {MP_ROM_QSTR(MP_QSTR_AppImage), MP_ROM_PTR(&mod_trezorapp_AppImage_type)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorapp_globals,
                            mp_module_trezorapp_globals_table);

const mp_obj_module_t mp_module_trezorapp = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorapp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorapp, mp_module_trezorapp);

#endif  // MICROPY_PY_TREZORAPP
