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

#pragma once

#include <sys/sysevent.h>
#include <sys/system.h>
#include <sys/systick.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_IPC
#include <sys/ipc.h>
#endif

#include "bip32.h"

#ifndef USE_DBG_CONSOLE
// temporary hack to allow compilation when DBG console is disabled
ssize_t dbg_console_write(const void* data, size_t data_size);
#endif

typedef struct {
  int (*hdnode_deserialize_public)(const char* str, uint32_t version,
                                   const char* curve, HDNode* node,
                                   uint32_t* fingerprint);
} trezor_crypto_v1_t;

typedef struct {
  void (*system_exit)(int exitcode);

  void (*system_exit_error)(const char* title, const char* message,
                            const char* footer);

  void (*system_exit_error_ex)(const char* title, size_t title_len,
                               const char* message, size_t message_len,
                               const char* footer, size_t footer_len);

  void (*system_exit_fatal)(const char* message, const char* file, int line);

  void (*system_exit_fatal_ex)(const char* message, size_t message_len,
                               const char* file, size_t file_len, int line);

  ssize_t (*dbg_console_write)(const void* data, size_t size);

  uint32_t (*systick_ms)(void);

  void (*sysevents_poll)(const sysevents_t* awaited, sysevents_t* signalled,
                         uint32_t deadline);

  ssize_t (*syshandle_read)(syshandle_t handle, void* buffer,
                            size_t buffer_size);

  bool (*ipc_register)(systask_id_t remote, void* buffer, size_t size);

  void (*ipc_unregister)(systask_id_t remote);

  bool (*ipc_try_receive)(ipc_message_t* msg);

  void (*ipc_message_free)(ipc_message_t* msg);

  bool (*ipc_send)(systask_id_t remote, uint32_t fn, const void* data,
                   size_t data_size);

  const trezor_crypto_v1_t* trezor_crypto_v1;

} trezor_api_v1_t;
