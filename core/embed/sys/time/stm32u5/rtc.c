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
#include <sys/rtc.h>
#include <sys/suspend.h>

// RTC driver structure
typedef struct {
  bool initialized;
  RTC_HandleTypeDef hrtc;
  rtc_wakeup_callback_t callback;
  void* callback_context;
} rtc_driver_t;

// RTC driver instance
static rtc_driver_t g_rtc_driver = {
    .initialized = false,
};

static uint32_t rtc_calendar_to_timestamp(const RTC_DateTypeDef* date,
                                          const RTC_TimeTypeDef* time);

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
  RCC->APB3SMENR |= RCC_APB3SMENR_RTCAPBSMEN;
  RCC->SRDAMR |= RCC_SRDAMR_RTCAPBAMEN;

  NVIC_ClearPendingIRQ(RTC_IRQn);
  NVIC_SetPriority(RTC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(RTC_IRQn);

  drv->initialized = true;
  return true;
}

bool rtc_get_timestamp(uint32_t* timestamp) {
  rtc_driver_t* drv = &g_rtc_driver;

  if (!drv->initialized || timestamp == NULL) {
    return false;
  }

  RTC_DateTypeDef date;
  RTC_TimeTypeDef time;

  // Get current time and date,
  // Important: GetTime has to be called before the GetDate in order to unlock
  // the values in higher-order callendar.
  if (HAL_OK != HAL_RTC_GetTime(&drv->hrtc, &time, RTC_FORMAT_BCD)) {
    return false;
  }

  // Get the current date
  if (HAL_OK != HAL_RTC_GetDate(&drv->hrtc, &date, RTC_FORMAT_BCD)) {
    return false;
  }

  *timestamp = rtc_calendar_to_timestamp(&date, &time);

  return true;
}

bool rtc_wakeup_timer_start(uint32_t seconds, rtc_wakeup_callback_t callback,
                            void* context) {
  rtc_driver_t* drv = &g_rtc_driver;

  if (!drv->initialized) {
    return false;
  }

  if (seconds < 1 || seconds > 0x10000) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->callback = callback;
  drv->callback_context = context;
  irq_unlock(irq_key);

  HAL_StatusTypeDef status;

  status = HAL_RTCEx_SetWakeUpTimer_IT(&drv->hrtc, seconds - 1,
                                       RTC_WAKEUPCLOCK_CK_SPRE_16BITS, 0);
  if (HAL_OK != status) {
    return false;
  }

  return true;
}

void rtc_wakeup_timer_stop(void) {
  rtc_driver_t* drv = &g_rtc_driver;

  if (!drv->initialized) {
    return;
  }

  HAL_RTCEx_DeactivateWakeUpTimer(&drv->hrtc);
  drv->callback = NULL;
  drv->callback_context = NULL;
}

void RTC_IRQHandler(void) {
  rtc_driver_t* drv = &g_rtc_driver;

  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  if (READ_BIT(RTC->MISR, RTC_MISR_WUTMF) != 0U) {
    // Clear the wakeup timer interrupt flag
    WRITE_REG(RTC->SCR, RTC_SCR_CWUTF);

    rtc_wakeup_callback_t callback = drv->callback;
    void* callback_context = drv->callback_context;

    // Deactivate the wakeup timer to prevent re-triggering
    rtc_wakeup_timer_stop();

    if (callback != NULL) {
      callback(callback_context);
    } else {
      wakeup_flags_set(WAKEUP_FLAG_RTC);
    }
  }

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

static const uint8_t days_in_month[] = {
    31,  // January
    28,  // February (not considering leap years here)
    31,  // March
    30,  // April
    31,  // May
    30,  // June
    31,  // July
    31,  // August
    30,  // September
    31,  // October
    30,  // November
    31   // December
};

static uint8_t bcd2bin(uint8_t val) { return (val & 0x0F) + ((val >> 4) * 10); }

// Check for leap year
static int is_leap_year(int year) {
  return ((year % 4 == 0 && year % 100 != 0) || (year % 400 == 0));
}

static uint32_t rtc_calendar_to_timestamp(const RTC_DateTypeDef* date,
                                          const RTC_TimeTypeDef* time) {
  uint8_t year = bcd2bin(date->Year);    // 0..99
  uint8_t month = bcd2bin(date->Month);  // 1..12
  uint8_t day = bcd2bin(date->Date);     // 1..31
  uint8_t hour = bcd2bin(time->Hours);
  uint8_t min = bcd2bin(time->Minutes);
  uint8_t sec = bcd2bin(time->Seconds);

  // STM RTC starts at 2000, so we need to offset the year evey time we
  // calculate the leap years.

  uint32_t days = 0;
  for (int y = 0; y < year; ++y) {
    days += 365;
    if (is_leap_year(y + 2000)) days += 1;
  }
  for (int m = 1; m < month; ++m) {
    days += days_in_month[m - 1];
    if (m == 2 && is_leap_year(year + 2000)) days += 1;
  }
  days += day - 1;

  uint32_t seconds = days * 86400 + hour * 3600 + min * 60 + sec;

  // Unix epoch starts at 1970, STM32 RTC at 2000
  // 946684800 = seconds from 1970-01-01 to 2000-01-01
  return seconds + 946684800;
}

#endif  // KERNEL_MODE
