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

#ifndef __TREZOR_PROFILE_H__
#define __TREZOR_PROFILE_H__

// TREZOR_PROFILE environment variable can be a full path
// or just a name that will result in the path:
//   ~/${PROFILE_HOMEDOT}/${TREZOR_PROFILE}
// If the variable is not set the default is ${PROFILE_DEFAULT}

#ifndef PROFILE_DEFAULT
#define PROFILE_DEFAULT "/var/tmp"
#endif

#ifndef PROFILE_HOMEDOT
#define PROFILE_HOMEDOT ".trezoremu"
#endif

void profile_init(void);
const char *profile_dir(void);
const char *profile_flash_path(void);
const char *profile_sdcard_path(void);

#endif // __TREZOR_PROFILE_H__
