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

#include <stdlib.h>

#include <sys/bootutils.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_IPC
#include <sys/ipc.h>
#endif

void system_init(systask_error_handler_t error_handler) {
  systick_init();
  systimer_init();
  systask_scheduler_init(error_handler);
#ifdef USE_IPC
  ipc_init();
#endif
#ifdef USE_DBG_CONSOLE
  dbg_console_init();
#endif
}

void system_deinit(void) { systick_deinit(); }

const char* system_fault_message(const system_fault_t* fault) {
  // Not used in simulator
  return "(FAULT)";
}

void system_emergency_rescue(systask_error_handler_t error_handler,
                             const systask_postmortem_t* pminfo) {
  if (error_handler != NULL) {
    error_handler(pminfo);
  }

  // We should never reach this point
  reboot_device();
}
