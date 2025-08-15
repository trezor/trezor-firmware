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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <sys/sysevent_source.h>

#include "dbg_internal.h"

static bool on_check_write_ready(void *context, systask_id_t task_id,
                                 void *param) {
  return true;  // Always ready to write
}

static void on_poll(void *context, bool read_awaited, bool write_awaited) {
  UNUSED(context);
  UNUSED(read_awaited);

  if (write_awaited) {
    syshandle_signal_write_ready(SYSHANDLE_DBG_CONSOLE, NULL);
  }
}

static ssize_t on_read(void *context, void *buffer, size_t buffer_size) {
  return dbg_read_internal(buffer, buffer_size);
}

static ssize_t on_write(void *context, const void *data, size_t data_size) {
  return dbg_write_internal(data, data_size);
}

static const syshandle_vmt_t dbg_console_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = NULL,
    .check_write_ready = on_check_write_ready,
    .poll = on_poll,
    .read = on_read,
    .write = on_write,
};

void dbg_console_init(void) {
  syshandle_register(SYSHANDLE_DBG_CONSOLE, &dbg_console_vmt, NULL);
}

#endif  // KERNEL_MODE
