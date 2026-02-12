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

/// class IpcMessage(NamedTuple):
///     """
///     IPC message structure.
///     """
///     remote: int
///     fn: int
///     data: AnyBytes

STATIC mp_obj_t mod_trezorio_ipc_message_to_obj(ipc_message_t* message) {
  const mp_obj_t values[3] = {
      MP_OBJ_NEW_SMALL_INT(message->remote),
      MP_OBJ_NEW_SMALL_INT(message->fn),
      mp_obj_new_bytes(message->data, message->size),
  };
  static const qstr fields[3] = {MP_QSTR_remote, MP_QSTR_fn, MP_QSTR_data};
  return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), values);
}
