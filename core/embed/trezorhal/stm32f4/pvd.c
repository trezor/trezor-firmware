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

#include TREZOR_BOARD
#include STM32_HAL_H

#include "bootutils.h"
#include "irq.h"
#include "mpu.h"

#if defined(KERNEL_MODE) && defined(USE_PVD)

void pvd_init(void) {
  // enable the PVD (programmable voltage detector).
  // select the "2.8V" threshold (level 5).
  // this detector will be active regardless of the
  // flash option byte BOR setting.
  __HAL_RCC_PWR_CLK_ENABLE();
  PWR_PVDTypeDef pvd_config = {0};
  pvd_config.PVDLevel = PWR_PVDLEVEL_5;
  pvd_config.Mode = PWR_PVD_MODE_IT_RISING_FALLING;
  HAL_PWR_ConfigPVD(&pvd_config);
  HAL_PWR_EnablePVD();
#ifdef STM32U5
  NVIC_SetPriority(PVD_PVM_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(PVD_PVM_IRQn);
#else
  NVIC_SetPriority(PVD_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(PVD_IRQn);
#endif
}

#ifdef STM32U5
void PVD_PVM_IRQHandler(void) {
#else
void PVD_IRQHandler(void) {
#endif
  mpu_reconfig(MPU_MODE_DEFAULT);
#ifdef BACKLIGHT_PWM_TIM
  // Turn off display backlight
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = 0;
#endif
  // from util.s
  extern void shutdown_privileged(void);
  shutdown_privileged();
}

#endif  // defined(KERNEL_MODE) && defined(USE_PVD)
