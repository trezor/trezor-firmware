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

#ifndef TREZORHAL_OPTION_BYTES_H
#define TREZORHAL_OPTION_BYTES_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

secbool flash_check_option_bytes(void);
void flash_lock_option_bytes(void);
void flash_unlock_option_bytes(void);
uint32_t flash_set_option_bytes(void);
secbool flash_configure_option_bytes(void);

void check_oem_keys(void);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_OPTION_BYTES_H
