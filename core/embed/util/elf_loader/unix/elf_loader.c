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

#include <sys/coreapp.h>
#include <util/elf_loader.h>

#include <dlfcn.h>

bool elf_load(applet_t *applet, const char *filename) {
  applet_layout_t layout = {0};
  applet_privileges_t privileges = {0};

  applet_init(applet, &layout, &privileges);

  applet->handle = dlopen(filename, RTLD_NOW);

  if (applet->handle == NULL) {
    // Failed to load the applet
    return false;
  }

  void *entrypoint = dlsym(applet->handle, "applet_main");

  if (entrypoint == NULL) {
    // Applet entry point not found
    dlclose(applet->handle);
    applet->handle = NULL;
    return false;
  }

  if (!systask_init(&applet->task, 0, 0, 0, applet)) {
    return false;
  }

  uintptr_t api_getter = (uintptr_t)coreapp_get_api_getter();

  if (!systask_push_call(&applet->task, entrypoint, api_getter, 0, 0)) {
    return false;
  }

  return true;
}

void applet_unload(applet_t *applet) {
  // Unload the applet
  dlclose(applet->handle);
}
