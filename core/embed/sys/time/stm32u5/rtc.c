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

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/power_manager.h>
#include <sys/rtc.h>

// RTC driver structure
typedef struct {
  bool initialized;
  RTC_HandleTypeDef hrtc;
} rtc_driver_t;

// RTC driver instance
static rtc_driver_t g_rtc_driver = {
    .initialized = false,
};

bool rtc_init(void) {
  rtc_driver_t* drv = &g_rtc_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(rtc_driver_t));

  drv->hrtc.Instance = RTC;
  drv->hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
  drv->hrtc.Init.AsynchPrediv = 128 - 1;
  drv->hrtc.Init.SynchPrediv = 256 - 1;
  drv->hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
  drv->hrtc.Init.BinMode = RTC_BINARY_NONE;

  if (HAL_OK != HAL_RTC_Init(&drv->hrtc)) {
    return false;
  }

  // Allow waking up from STOP mode
  RCC->APB3SMENR &= ~RCC_APB3SMENR_RTCAPBSMEN;
  RCC->SRDAMR |= RCC_SRDAMR_RTCAPBAMEN;

  NVIC_ClearPendingIRQ(RTC_IRQn);
  NVIC_SetPriority(RTC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(RTC_IRQn);

  drv->initialized = true;
  return true;
}

bool rtc_wakeup_timer_start(uint32_t seconds) {
  rtc_driver_t* drv = &g_rtc_driver;

  if (!drv->initialized) {
    return false;
  }

  if (seconds < 1 || seconds > 0x10000) {
    return false;
  }

  HAL_StatusTypeDef status;

  status = HAL_RTCEx_SetWakeUpTimer_IT(&drv->hrtc, seconds - 1,
                                       RTC_WAKEUPCLOCK_CK_SPRE_16BITS, 0);
  if (HAL_OK != status) {
    return false;
  }

  return true;
}

void RTC_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  if (READ_BIT(RTC->MISR, RTC_MISR_WUTMF) != 0U) {
    // Clear the wakeup timer interrupt flag
    WRITE_REG(RTC->SCR, RTC_SCR_CWUTF);
    // Deactivate the wakeup timer to prevent re-triggering
    HAL_RTCEx_DeactivateWakeUpTimer(&g_rtc_driver.hrtc);
    // Signal the wakeup event to the power manager
    pm_wakeup_flags_set(PM_WAKEUP_FLAG_RTC);
  }

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

#endif  // KERNEL_MODE
