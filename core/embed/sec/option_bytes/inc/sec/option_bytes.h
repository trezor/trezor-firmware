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

#pragma once

#include <trezor_types.h>

#ifdef SECURE_MODE

/**
 * @brief Configure MCU option bytes to the expected secure values if needed.
 *
 * @return sectrue if option bytes were already correctly configured and no
 * changes were required; returns secfalse if the routine had to update the
 * option bytes (a reset/relaunch may follow as part of the procedure).
 */
secbool option_bytes_configure(void);

/**
 * @brief Perform a sanity check on OEM key lock status bits to ensure OEM keys
 * are not programmed (should be 0xFFFFFFFF).
 *
 * Triggers a panic via ensure() if a key is detected as set.
 */
void option_bytes_check_oem_keys(void);

#endif  // SECURE_MODE
