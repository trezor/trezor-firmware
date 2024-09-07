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

#include "mpu.h"

void mpu_init(void) {
  // MPU functions are not fully implemented in Emulator
}

mpu_mode_t mpu_get_mode(void) { return MPU_MODE_DISABLED; }

mpu_mode_t mpu_reconfig(mpu_mode_t mode) { return MPU_MODE_DISABLED; }

void mpu_restore(mpu_mode_t mode) {}
