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

#include <util/app_loader.h>

/// package: trezorapp

/// class AppTask:
///     """
///     App task structure.
///     """
typedef struct _mp_obj_AppTask_t {
  mp_obj_base_t base;
  systask_id_t task_id;
} mp_obj_AppTask_t;

/// def __init__(self, task_id: int) -> None:
///     """
///     Creates an app task object for the given internal task ID.
///     """
STATIC mp_obj_t mod_trezorapp_AppTask_make_new(const mp_obj_type_t *type,
                                               size_t n_args, size_t n_kw,
                                               const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 1, 1, false);
  mp_int_t task_id = mp_obj_get_int(args[0]);
  mp_obj_AppTask_t *o = mp_obj_malloc(mp_obj_AppTask_t, type);
  o->task_id = task_id;
  return MP_OBJ_FROM_PTR(o);
}

/// def id(self) -> int:
///     """
///     Returns the task id.
///     """
STATIC mp_obj_t mod_trezorapp_AppTask_id(mp_obj_t self) {
  mp_obj_AppTask_t *o = MP_OBJ_TO_PTR(self);
  return MP_OBJ_NEW_SMALL_INT(o->task_id);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppTask_id_obj,
                                 mod_trezorapp_AppTask_id);

/// def is_running(self) -> bool:
///     """
///     Returns whether the application is still running.
///     """
STATIC mp_obj_t mod_trezorapp_AppTask_is_running(mp_obj_t self) {
  mp_obj_AppTask_t *o = MP_OBJ_TO_PTR(self);

  if (app_task_is_running(o->task_id)) {
    return mp_const_true;
  } else {
    return mp_const_false;
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppTask_is_running_obj,
                                 mod_trezorapp_AppTask_is_running);

/// def unload(self) -> None:
///     """
///     Unloads the application associated with this task.
///     """
STATIC mp_obj_t mod_trezorapp_AppTask_unload(mp_obj_t self) {
  mp_obj_AppTask_t *o = MP_OBJ_TO_PTR(self);

  app_task_unload(o->task_id);
  o->task_id = 0;

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppTask_unload_obj,
                                 mod_trezorapp_AppTask_unload);

STATIC const mp_rom_map_elem_t mod_trezorapp_AppTask_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_id), MP_ROM_PTR(&mod_trezorapp_AppTask_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_running),
     MP_ROM_PTR(&mod_trezorapp_AppTask_is_running_obj)},
    {MP_ROM_QSTR(MP_QSTR_unload),
     MP_ROM_PTR(&mod_trezorapp_AppTask_unload_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorapp_AppTask_locals_dict,
                            mod_trezorapp_AppTask_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorapp_AppTask_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppTask,
    .locals_dict = (void *)&mod_trezorapp_AppTask_locals_dict,
    .make_new = mod_trezorapp_AppTask_make_new,
};
