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

#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "../../powerctl/npm1300/npm1300.h"
#include "power_manager_internal.h"

pm_status_t pm_control_hibernate() {
  // TEMPORARY FIX:
  // Enable Backup domain retentaion in VBAT mode before entering the
  // hiberbation. BREN bit can be accessed only in LDO mode.
  __HAL_RCC_PWR_CLK_ENABLE();

  // Switch to LDO regulator
  CLEAR_BIT(PWR->CR3, PWR_CR3_REGSEL);
  // Wait until system switch on new regulator
  while (HAL_IS_BIT_SET(PWR->SVMSR, PWR_SVMSR_REGS))
    ;
  // Enable backup domain retention
  PWR->BDCR1 |= PWR_BDCR1_BREN;

  if (!npm1300_enter_shipmode()) {
    return PM_ERROR;
  }

  // Wait for the device to power off
  systick_delay_ms(50);

  return PM_ERROR;
}
