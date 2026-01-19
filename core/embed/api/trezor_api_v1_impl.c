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

#include "trezor_api_v1.h"

#ifndef USE_DBG_CONSOLE
// temporary hack to allow compilation when DBG console is disabled
ssize_t dbg_console_write(const void* data, size_t data_size) {
  return data_size;
}
#endif

const trezor_crypto_v1_t trezor_crypto_v1 = {
    .hdnode_from_xpub = hdnode_from_xpub,
};

const trezor_api_v1_t trezor_api_v1 = {
    .system_exit = system_exit,
    .system_exit_error = system_exit_error,
    .system_exit_error_ex = system_exit_error_ex,
    .system_exit_fatal = system_exit_fatal,
    .system_exit_fatal_ex = system_exit_fatal_ex,
    .systick_ms = systick_ms,
    .sysevents_poll = sysevents_poll,
    .syshandle_read = syshandle_read,
    .dbg_console_write = dbg_console_write,
    .ipc_register = ipc_register,
    .ipc_unregister = ipc_unregister,
    .ipc_try_receive = ipc_try_receive,
    .ipc_message_free = ipc_message_free,
    .ipc_send = ipc_send,
    .trezor_crypto_v1 = &trezor_crypto_v1,
};

const void* coreapp_api_get(uint32_t version) {
  if (version == 1) {
    return &trezor_api_v1;
  }
  return NULL;
}
