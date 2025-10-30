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

#include <util/app_cache.h>

/// package: trezorio.app_cache

/// def spawn(app_id: str) -> int:
///     """
///     Spawns an application from the app cache and
///     returns its task ID.
///     """
STATIC mp_obj_t mod_trezorio_app_cache_spawn(mp_obj_t app_id_obj) {
  size_t app_id_size;
  const char* app_id = mp_obj_str_get_data(app_id_obj, &app_id_size);

  systask_id_t task_id;
  if (!app_cache_spawn(app_id, app_id_size, &task_id)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to spawn app from app cache."));
  }

  return MP_OBJ_NEW_SMALL_INT(task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_app_cache_spawn_obj,
                                 mod_trezorio_app_cache_spawn);

/// def unload(task_id: int) -> None:
///     """
///     Unloads the application with the specified task ID.
///     """
STATIC mp_obj_t mod_trezorio_app_cache_unload(mp_obj_t task_id_obj) {
  systask_id_t task_id = trezor_obj_get_uint(task_id_obj);
  app_cache_unload(task_id);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_app_cache_unload_obj,
                                 mod_trezorio_app_cache_unload);

STATIC const mp_rom_map_elem_t mod_trezorio_app_cache_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_app_cache)},
    {MP_ROM_QSTR(MP_QSTR_spawn), MP_ROM_PTR(&mod_trezorio_app_cache_spawn_obj)},
    {MP_ROM_QSTR(MP_QSTR_unload_app),
     MP_ROM_PTR(&mod_trezorio_app_cache_unload_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_app_cache_globals,
                            mod_trezorio_app_cache_globals_table);

STATIC const mp_obj_module_t mod_trezorio_app_cache_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_trezorio_app_cache_globals,
};
