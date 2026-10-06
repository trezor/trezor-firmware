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

#include <stdint.h>
#include <trezor_rtl.h>

#include <sys/ipc.h>

/// package: trezorio.__init__

/// def ipc_send(
///     remote: int,
///     service: int,
///     message_id: int,
///     data: AnyBytes,
/// ) -> None:
///     """
///     Sends an IPC message to the specified remote task.
///     """
static mp_obj_t mod_trezorio_ipc_send(size_t n_args, const mp_obj_t* args) {
  mp_obj_t remote_obj = args[0];
  mp_obj_t service_obj = args[1];
  mp_obj_t message_id_obj = args[2];
  mp_obj_t data_obj = args[3];

  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

  systask_id_t remote = (systask_id_t)mp_obj_get_int(remote_obj);
  mp_int_t service = mp_obj_get_int(service_obj);
  mp_int_t message_id = mp_obj_get_int(message_id_obj);
  if (service < 0 || service > UINT16_MAX || message_id < 0 ||
      message_id > UINT16_MAX) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid service or message ID."));
  }

  if (!ipc_send(remote, service, message_id, bufinfo.buf, bufinfo.len)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to send IPC message."));
  }
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_ipc_send_obj, 4, 4,
                                           mod_trezorio_ipc_send);

/// class IpcMessage(NamedTuple):
///     """
///     IPC message structure.
///     """
///     remote: int
///     service: int
///     message_id: int
///     data: AnyBytes

static mp_obj_t mod_trezorio_ipc_message_to_obj(ipc_message_t* message) {
  const mp_obj_t values[4] = {
      MP_OBJ_NEW_SMALL_INT(message->remote),
      MP_OBJ_NEW_SMALL_INT(message->service),
      MP_OBJ_NEW_SMALL_INT(message->message_id),
      mp_obj_new_bytes(message->data, message->size),
  };
  static const qstr fields[4] = {MP_QSTR_remote, MP_QSTR_service,
                                 MP_QSTR_message_id, MP_QSTR_data};
  return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), values);
}
