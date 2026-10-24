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

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <trezor_rtl.h>

#include <sys/profile.h>

#include <stdlib.h>

#define SVAR(varname)   \
  static char *varname; \
  if (varname) {        \
    return varname;     \
  }

#define GETENV(varname, envname, fallback)       \
  varname = getenv(envname);                     \
  if (varname && !*varname) {                    \
    error_shutdown(envname " is set but empty"); \
  }                                              \
  if (!varname) {                                \
    varname = fallback;                          \
  }

#define FILE_PATH(varname, filename)                              \
  if (asprintf(&varname, "%s/%s", profile_dir(), filename) < 0) { \
    varname = NULL;                                               \
  }                                                               \
  if (!varname) {                                                 \
    error_shutdown("asprintf failed");                            \
  }

const char *profile_name(void) {
  SVAR(_profile_name);
  GETENV(_profile_name, "TREZOR_PROFILE_NAME", PROFILE_NAME_DEFAULT);
  return _profile_name;
}

const char *profile_dir(void) {
  SVAR(_profile_dir);
  GETENV(_profile_dir, "TREZOR_PROFILE_DIR", PROFILE_DIR_DEFAULT);
  return _profile_dir;
}

const char *profile_flash_path(void) {
  SVAR(_flash_path);
  char *filename = NULL;
  GETENV(filename, "TREZOR_FLASH_FILENAME", "trezor.flash");
  FILE_PATH(_flash_path, filename);
  return _flash_path;
}

const char *profile_sdcard_path(void) {
  SVAR(_sdcard_path);
  char *filename = NULL;
  GETENV(filename, "TREZOR_SDCARD_FILENAME", "trezor.sdcard");
  FILE_PATH(_sdcard_path, filename);
  return _sdcard_path;
}

const char *profile_usb_disconnect_path(void) {
  SVAR(_disconnect_path);
  FILE_PATH(_disconnect_path, "trezor.usb_data_disconnected");
  return _disconnect_path;
}
