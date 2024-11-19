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

#ifndef TREZORHAL_MPU_H
#define TREZORHAL_MPU_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

// The MPU driver can be set to on of the following modes.
//
// In each mode, the MPU is configured to allow access to specific
// memory regions.
//
// The `MPU_MODE_DEFAULT` mode is the most restrictive and serves as
// a base for other modes.
typedef enum {
  MPU_MODE_DISABLED,      // MPU is disabled
  MPU_MODE_DEFAULT,       // Default
  MPU_MODE_BOARDCAPS,     // + boardloader capabilities (privileged RO)
  MPU_MODE_BOOTUPDATE,    // + bootloader area (privileged RW)
  MPU_MODE_BOOTARGS,      // + boot arguments (privileged RW)
  MPU_MODE_OTP,           // + OTP (privileged RW)
  MPU_MODE_FSMC_REGS,     // + FSMC control registers (privileged RW)
  MPU_MODE_FLASHOB,       // + Option bytes mapping (privileged RW)
  MPU_MODE_SECRET,        // + secret area (privileged RW)
  MPU_MODE_STORAGE,       // + both storage areas (privileged RW)
  MPU_MODE_ASSETS,        // + assets (privileged RW)
  MPU_MODE_SAES,          // + unprivileged SAES code
  MPU_MODE_UNUSED_FLASH,  // + unused flash areas (privileged RW)
  MPU_MODE_APP,           // + unprivileged DMA2D (RW) & Assets (RO)
} mpu_mode_t;

// Initializes the MPU and sets it to MPU_MODE_DISABLED.
//
// This function should be called before any other MPU function.
void mpu_init(void);

// Returns the current MPU mode.
//
// If the MPU is not initialized, returns MPU_MODE_DISABLED.
mpu_mode_t mpu_get_mode(void);

// Reconfigures the MPU to the given mode and returns the previous mode.
//
// If the MPU is not initialized, does nothing and returns MPU_MODE_DISABLED.
mpu_mode_t mpu_reconfig(mpu_mode_t mode);

// Restores the MPU to the given mode.
//
// Same as `mpu_reconfig()`, but with a more descriptive name.
void mpu_restore(mpu_mode_t mode);

// Sets the MPU to allow access to the
// framebuffer at the given address and size.
//
// The changes are made effective after the next MPU reconfiguration
// to the `MPU_MODE_APP` or `MPU_MODE_DEFAULT` mode.
//
// Addr and size must be aligned to the 32-byte boundary.
// If addr == 0, the framebuffer is not accessible.
void mpu_set_active_fb(void* addr, size_t size);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_MPU_H
