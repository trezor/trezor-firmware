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

#ifdef USE_BLE
#include <io/ble.h>
#endif

/**
 * @brief Switches the CPU to STOP2 low-power mode.
 *
 * This function blocks until an interrupt wakes the CPU.
 * Upon wake-up, it restores the system clock so the CPU can run at full speed.
 */
void power_save_suspend_cpu(void);

/**
 * @brief State of the drivers before entering a low-power mode
 *        used to restore them after wake-up.
 */
typedef struct {
#ifdef USE_BACKLIGHT
  /** Backlight level */
  int backlight_level;
#endif
#ifdef USE_BLE
  /** State of the ble driver */
  ble_wakeup_params_t ble;
#endif
} power_save_wakeup_params_t;

/**
 * @brief Suspends I/O drivers.
 *
 * This function is called before the device enters a low-power state.
 * It suspends I/O drivers to reduce power consumption.
 *
 * @param wakeup_params Pointer to a structure that will be filled with
 *                      the state of the drivers before entering low-power mode.
 */
void power_save_suspend_io(power_save_wakeup_params_t *wakeup_params);

/**
 * @brief Resumes I/O drivers.
 *
 * This function is called when the device exits a low-power state.
 * It resumes I/O drivers that were suspended before entering
 * the low-power state.
 *
 * @param wakeup_params Pointer to a structure that contains the state of the
 *                      drivers before entering low-power mode.
 */
void power_save_resume_io(const power_save_wakeup_params_t *wakeup_params);

/**
 * @brief Suspends secure peripherals.
 *
 * This function is called before the device enters a low-power state.
 * It suspends secure peripherals to reduce power consumption.
 */
void power_save_suspend_secure_io(void);

/**
 * @brief Resumes secure peripherals.
 *
 * This function is called when the device exits a low-power state.
 * It resumes secure peripherals that were suspended before entering
 * the low-power state.
 */
void power_save_resume_secure_io(void);
