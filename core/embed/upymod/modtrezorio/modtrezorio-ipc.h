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

#include <sys/ipc.h>

/// package: trezorio.__init__

/// def ipc_send(remote: int, fn: int, data: AnyBytes) -> None:
///     """
///     Sends an IPC message to the specified remote task.
///     """
STATIC mp_obj_t mod_trezorio_ipc_send(mp_obj_t remote_obj, mp_obj_t fn_obj,
                                      mp_obj_t data_obj) {
  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

  systask_id_t remote = (systask_id_t)mp_obj_get_int(remote_obj);
  uint32_t fn = (uint32_t)mp_obj_get_int(fn_obj);

  if (!ipc_send(remote, fn, bufinfo.buf, bufinfo.len)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to send IPC message."));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_ipc_send_obj,
                                 mod_trezorio_ipc_send);

/// class IpcMessage:
///     """
///     IPC message structure.
///     """
typedef struct _mp_obj_IpcMessage_t {
  mp_obj_base_t base;
  ipc_message_t message;
} mp_obj_IpcMessage_t;

/// def fn(self) -> int:
///     """
///     Returns the function number.
///     """
STATIC mp_obj_t mod_trezorio_IpcMessage_fn(mp_obj_t self) {
  mp_obj_IpcMessage_t *o = MP_OBJ_TO_PTR(self);
  return MP_OBJ_NEW_SMALL_INT(o->message.fn);  // !@# uint
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_IpcMessage_fn_obj,
                                 mod_trezorio_IpcMessage_fn);

/// def remote(self) -> int:
///     """
///     Returns the remote task ID.
///     """
STATIC mp_obj_t mod_trezorio_IpcMessage_remote(mp_obj_t self) {
  mp_obj_IpcMessage_t *o = MP_OBJ_TO_PTR(self);
  return MP_OBJ_NEW_SMALL_INT(o->message.remote);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_IpcMessage_remote_obj,
                                 mod_trezorio_IpcMessage_remote);

/// def free(self) -> None:
///     """
///     Frees the IPC message resources.
///     """
STATIC mp_obj_t mod_trezorio_IpcMessage_free(mp_obj_t self) {
  mp_obj_IpcMessage_t *o = MP_OBJ_TO_PTR(self);

  ipc_message_free(&o->message);
  memset(&o->message, 0, sizeof(ipc_message_t));

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_IpcMessage_free_obj,
                                 mod_trezorio_IpcMessage_free);

/// def data(self) -> bytes:
///     """
///     Returns the IPC message data as bytes.
///     """
STATIC mp_obj_t mod_trezorio_IpcMessage_data(mp_obj_t self) {
  mp_obj_IpcMessage_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_bytes(o->message.data, o->message.size);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_IpcMessage_data_obj,
                                 mod_trezorio_IpcMessage_data);

STATIC const mp_rom_map_elem_t mod_trezorio_IpcMessage_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_remote),
     MP_ROM_PTR(&mod_trezorio_IpcMessage_remote_obj)},
    {MP_ROM_QSTR(MP_QSTR_fn), MP_ROM_PTR(&mod_trezorio_IpcMessage_fn_obj)},
    {MP_ROM_QSTR(MP_QSTR_data), MP_ROM_PTR(&mod_trezorio_IpcMessage_data_obj)},
    {MP_ROM_QSTR(MP_QSTR_free), MP_ROM_PTR(&mod_trezorio_IpcMessage_free_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_IpcMessage_locals_dict,
                            mod_trezorio_IpcMessage_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_IpcMessage_type = {
    {&mp_type_type},
    .name = MP_QSTR_IpcMessage,
    .locals_dict = (void *)&mod_trezorio_IpcMessage_locals_dict,
};
