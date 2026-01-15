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

#include <io/elf_loader.h>
#include <sys/coreapp.h>
#include <sys/logging.h>

#include <dlfcn.h>
#include <unistd.h>

LOG_DECLARE(elf_loader)

static void elf_applet_unload(applet_t* applet) {
  if (applet->handle != NULL) {
    // Unload dynamic library
    dlclose(applet->handle);
  }
}

ts_t write_to_file(const char* filename, const void* elf_ptr, size_t elf_size) {
  TSH_DECLARE;

  FILE* f = fopen(filename, "wb");
  TSH_CHECK(f != NULL, TS_EIO);

  int rc = fwrite(elf_ptr, 1, elf_size, f);
  TSH_CHECK(rc == elf_size, TS_EIO);

cleanup:
  if (f != NULL) {
    fclose(f);
  }

  TSH_RETURN;
}

ts_t elf_load(applet_t* applet, const void* elf_ptr, size_t elf_size) {
  TSH_DECLARE;
  ts_t status;

  applet_privileges_t privileges = {0};

  applet_init(applet, &privileges, elf_applet_unload);

  const char* filename = "/tmp/trezor_ext_app.so";

  // Copy the image to the temporary file that will be
  // unlinked just after it's loaded
  status = write_to_file(filename, elf_ptr, elf_size);
  TSH_CHECK_OK(status);

  applet->handle = dlopen(filename, RTLD_NOW);
  unlink(filename);
  if (applet->handle == NULL) {
    LOG_ERR("dlopen failed: %s", dlerror());
  }
  TSH_CHECK(applet->handle != NULL, TS_EINVAL);

  void* entrypoint = dlsym(applet->handle, "applet_main");
  TSH_CHECK(entrypoint != NULL, TS_EINVAL);

  bool ok = systask_init(&applet->task, 0, 0, 0, applet);
  TSH_CHECK(ok, TS_ENOMEM);

  uintptr_t api_getter = (uintptr_t)coreapp_get_api_getter();

  ok = systask_push_call(&applet->task, entrypoint, api_getter, 0, 0);
  TSH_CHECK(ok, TS_ENOMEM);

  TSH_RETURN;

cleanup:
  applet_unload(applet);

  TSH_RETURN;
}
