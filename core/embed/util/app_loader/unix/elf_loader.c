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
#include <unistd.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

static void elf_applet_unload(applet_t* applet) {
  if (applet->handle != NULL) {
    // Unload dynamic library
    dlclose(applet->handle);
  }
}

bool write_to_file(const char* filename, const void* elf_ptr, size_t elf_size) {
  FILE* f = fopen(filename, "wb");

  if (f == NULL) {
    return false;
  }

  int rc = fwrite(elf_ptr, 1, elf_size, f);

  fclose(f);

  return rc == elf_size;
}

bool elf_load(applet_t* applet, const void* elf_ptr, size_t elf_size) {
  applet_privileges_t privileges = {0};

  applet_init(applet, &privileges, elf_applet_unload);

  const char* filename = "/tmp/trezor_ext_app.so";

  // Copy the image to the temporary file that will be
  // unlinked just after it's loaded
  if (!write_to_file(filename, elf_ptr, elf_size)) {
    goto cleanup;
  }

  applet->handle = dlopen(filename, RTLD_NOW);

  unlink(filename);

  if (applet->handle == NULL) {
#ifdef USE_DBG_CONSOLE
    dbg_printf("elf_load: %s\n", dlerror());
#endif
    // Failed to load the applet
    goto cleanup;
  }

  void* entrypoint = dlsym(applet->handle, "applet_main");

  if (entrypoint == NULL) {
    // Applet entry point not found
    goto cleanup;
  }

  if (!systask_init(&applet->task, 0, 0, 0, applet)) {
    goto cleanup;
  }

  uintptr_t api_getter = (uintptr_t)coreapp_get_api_getter();

  if (!systask_push_call(&applet->task, entrypoint, api_getter, 0, 0)) {
    goto cleanup;
  }

  return true;

cleanup:
  applet_unload(applet);
  return false;
}
