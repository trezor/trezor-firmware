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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/cpuid.h>
#include <sys/mpu.h>

#ifdef STM32U5
#include "stm32u5xx_ll_utils.h"
#else
#include "stm32f4xx_ll_utils.h"
#endif

void cpuid_get(cpuid_t* cpuid) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);
  cpuid->id[0] = LL_GetUID_Word0();
  cpuid->id[1] = LL_GetUID_Word1();
  cpuid->id[2] = LL_GetUID_Word2();
  mpu_restore(mpu_mode);
}

#endif
