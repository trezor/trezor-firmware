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

#ifdef KERNEL

#include <trezor_rtl.h>

#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/systask.h>

extern int coreapp_emu(int argc, char** argv);

// API getter function implemented in the coreapp
extern const void* coreapp_api_get(uint32_t version);

bool coreapp_init(applet_t* applet, int argc, char** argv) {
  const applet_privileges_t coreapp_privileges = {0};

  applet_init(applet, &coreapp_privileges, NULL);

  if (!systask_init(&applet->task, 0, 0, 0, applet)) {
    return false;
  }

  if (!systask_push_call(&applet->task, (void*)coreapp_emu, (uintptr_t)argc,
                         (uintptr_t)argv, 0)) {
    return false;
  }

  return true;
}

#ifdef USE_APP_LOADING
void* coreapp_get_api_getter(void) { return (void*)coreapp_api_get; }
#endif

#endif  // KERNEL
