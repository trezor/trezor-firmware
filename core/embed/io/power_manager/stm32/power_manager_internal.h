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

#include <trezor_bsp.h>
#include <trezor_types.h>

#include <io/pmic.h>
#include <io/power_manager.h>
#ifdef USE_RTC
// Only for rtc_event_id_t below; every RTC user in this module is USE_RTC-only.
#include <sys/rtc_scheduler.h>
#endif
#include <sys/systimer.h>

#ifdef USE_WIRELESS_CHARGER
// The only wireless-charger driver so far; included only on boards that have
// one, so a board without wireless never compiles the policy against a chip
// it does not carry.
#include "../wireless/stwlc38/stwlc38.h"
#endif

#include "../core/pm_core.h"

// Glue side of the policy: what stm32/power_manager.c owns around the pure
// core in pm_core.h - the lock, the sampling timer, suspend bookkeeping, the
// RTC, backup RAM and the hardware sub-drivers.

// --- Glue constants ----------------------------------------------------------

// Timeout after which the device automatically transit from suspend to
// hibernation
#define PM_AUTO_HIBERNATE_TIMEOUT_S (2 * 60 * 60)  // 2 hours

// How long pm_init()/pm_suspend() wait for the first meaningful sample
#define PM_STABILIZATION_TIMEOUT_MS 2000

// --- Board tunables ----------------------------------------------------------
// Supplied by the board header (<trezor_bsp.h>), because they describe the
// board and its battery pack rather than the policy. Required, not defaulted:
// a missing value is a build error naming it, not a silently inherited number
// from another product. See docs/core/embed-arch/power-manager.md.
//
//   BATTERY_LOW_SOC_PERCENT          SoC [%] at/below which power-save starts
//   PM_POWER_SAVE_BACKLIGHT_LIMIT    backlight cap in power-save mode (0-255)
//   PM_SUSPEND_CURRENT_MA            board drain in suspend [mA]     (USE_RTC)
//   PM_HIBERNATION_CURRENT_MA        board drain in hibernation [mA] (USE_RTC)
//   BATTERY_CHARGING_CURRENT_MAX_MA  pack's max charging current [mA]
//                                    (charger leaf only, core/charging.c)
//   BATTERY_CHARGE_TEMP_BANDS        {max_temp_C, current factor} bands,
//                                    ascending (charger leaf only)
//
// The glue hands them to the core as a pm_config_t; the charger leaf reads
// its own directly.

#ifndef BATTERY_LOW_SOC_PERCENT
#error "Board header must define BATTERY_LOW_SOC_PERCENT"
#endif
#ifndef PM_POWER_SAVE_BACKLIGHT_LIMIT
#error "Board header must define PM_POWER_SAVE_BACKLIGHT_LIMIT"
#endif
#ifdef USE_RTC
#ifndef PM_SUSPEND_CURRENT_MA
#error "Board header must define PM_SUSPEND_CURRENT_MA"
#endif
#ifndef PM_HIBERNATION_CURRENT_MA
#error "Board header must define PM_HIBERNATION_CURRENT_MA"
#endif
#endif

// Power manager driver (glue) structure
typedef struct {
  bool initialized;

  // The policy
  pm_core_t core;

  // Set if the driver was requested to suspend background operations.
  // IF so, the driver waits until the last operation is finished,
  // then enters suspended mode.
  bool suspending;

  // Set if the driver's background operations are suspended.
  bool suspended;

  // Latest wireless-charger report, for pm_get_report()
#ifdef USE_WIRELESS_CHARGER
  stwlc38_report_t wireless_data;
#endif

  // Timers and timestamps
  systimer_t* monitoring_timer;
  uint32_t suspend_timestamp;
  uint32_t last_active_timestamp;
#ifdef USE_RTC
  rtc_event_id_t autohibernate_event_id;
#endif

} pm_driver_t;

// Shared global driver instance
extern pm_driver_t g_pm;

// Store power manager data to backup RAM
pm_status_t pm_store_data_to_backup_ram(void);

#ifdef USE_RTC
// Schedule the RTC wakeup when going into suspend mode.
// Return false if the driver was not initialized or the RTC timestamp is
// not available.
bool pm_schedule_rtc_wakeup(void);
#endif
