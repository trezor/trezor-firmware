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

#include <sys/applet.h>
#include <sys/systask.h>

#ifdef KERNEL

void applet_init(applet_t* applet, const applet_privileges_t* privileges,
                 applet_unload_cb_t unload_cb) {
  memset(applet, 0, sizeof(applet_t));

  applet->unload_cb = unload_cb;

  if (privileges != NULL) {
    applet->privileges = *privileges;
  }
}

void applet_run(applet_t* applet) { systask_yield_to(&applet->task); }

void applet_unload(applet_t* applet) {
  if (applet->task.id > 0) {
    if (systask_is_alive(&applet->task)) {
      systask_exit(&applet->task, 0);
    }
  }

  if (applet->unload_cb != NULL) {
    applet->unload_cb(applet);
    applet->unload_cb = NULL;
  }
}

bool applet_is_alive(applet_t* applet) {
  return systask_is_alive(&applet->task);
}

applet_t* applet_active(void) {
  systask_t* task = systask_active();

  if (task == NULL) {
    return NULL;
  }

  return (applet_t*)task->applet;
}

#endif  // KERNEL
