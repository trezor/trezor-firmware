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

#include <trezor_bsp.h>  // required by #ifdef STM32U5 below (see #4306 issue)
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sys/mpu.h>

#ifdef STM32U5
#include "stm32u5xx_ll_utils.h"
#else
#include "stm32f4xx_ll_utils.h"
#endif

static void prodtest_get_cpuid(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t cpuid[3];

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);
  cpuid[0] = LL_GetUID_Word0();
  cpuid[1] = LL_GetUID_Word1();
  cpuid[2] = LL_GetUID_Word2();
  mpu_restore(mpu_mode);

  cli_ok_hexdata(cli, &cpuid, sizeof(cpuid));
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "get-cpuid",
  .func = prodtest_get_cpuid,
  .info = "Retrieve unique CPU ID",
  .args = ""
);


