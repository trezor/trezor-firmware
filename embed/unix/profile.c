/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/errno.h>
#include <libgen.h>
#include <unistd.h>

#include "profile.h"
#include "common.h"

static int mkpath(const char *path, mode_t mode) {
    if (!path) {
        errno = EINVAL;
        return 1;
    }
    
    struct stat sb;
    if (!stat(strdup(path), &sb)) {
        return 0;
    }

    // dirname has multiple incompatible implementations.
    // Some modify input argument some share output buffer.
    char *pathdup = strdup(path);
    char *subpath = strdup(dirname(pathdup));
    mkpath(subpath, mode);
    free(pathdup);
    free(subpath);
    return mkdir(path, mode);
}

void profile_init(void) {
    const char *dir = profile_dir();
    if (mkpath(dir, 0755)) {
        perror(dir);
        printf("!!! Unable to initialize profile directory `%s`. Quitting\n", dir);
        exit(1);
    }
    printf("Profile directory: %s\n", dir);
}

const char *profile_dir(void) {
    static const char *_profile_dir;
    
    if (_profile_dir) {
        return _profile_dir;
    }

    char *trezor_profile = getenv("TREZOR_PROFILE");
    if (!trezor_profile || strlen(trezor_profile) < 1) {
        trezor_profile = PROFILE_DEFAULT;
    }

    char *path;
    if (trezor_profile[0] == '/') {
    // TREZOR_PROFILE is a full path to profile directory
        path = strdup(trezor_profile);
    } else {
    // TREZOR_PROFILE is just a profile name and will be put in ~/.trezoremu/
        int print_length = asprintf(&path, "%s/" PROFILE_HOMEDOT "/%s", getenv("HOME"), trezor_profile);
        if (print_length == -1) {
            path = NULL;
        }
    }

    if (!path) { // last resort fallback
        path = PROFILE_DEFAULT;
    }

    _profile_dir = path;

    return _profile_dir;
}

const char *profile_flash_path(void) {
    static char *_flash_path;
    if (_flash_path) {
        return _flash_path;
    }

    if (asprintf(&_flash_path, "%s/trezor.flash", profile_dir()) < 0) {
        _flash_path = NULL;
    }

    if (!_flash_path) { // last resort fallback
        _flash_path = PROFILE_DEFAULT "/trezor.flash";
    }

    return _flash_path;
}

const char *profile_sdcard_path(void) {
    static char *_sdcard_path;
    if (_sdcard_path) {
        return _sdcard_path;
    }

    if (asprintf(&_sdcard_path, "%s/trezor.sdcard", profile_dir()) < 0) {
        _sdcard_path = NULL;
    }

    if (!_sdcard_path) { // last resort fallback
        _sdcard_path = PROFILE_DEFAULT "/trezor.sdcard";
    }

    return _sdcard_path;
}
