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

/**
 * @brief Initialize the RTC driver
 *
 * Before initialization, the RCC clock for the RTC must be configured to
 * 32.768 kHz (using either LSE or LSI).
 *
 * @return true if initialization was successful, false otherwise
 */
bool rtc_init(void);

/**
 * @brief Callback invoked when the RTC wakeup event occurs
 *
 * @param context Context pointer passed to rtc_wakeup_timer_start
 */
typedef void (*rtc_wakeup_callback_t)(void* context);

/**
 * @brief Schedule a wakeup event after a specified number of seconds
 *
 * Configures the RTC to wake up the system from STOP mode after the specified
 * number of seconds. After waking up, callback is called if not NULL otherwise
 * the WAKEUP_FLAG_RTC flag is set.
 *
 * @param seconds Number of seconds (1 to 65536) to wait before waking up.
 * @param callback Callback function to be called when the wakeup event occurs.
 * @param context Context pointer to be passed to the callback function.
 * @return true if the wakeup was successfully scheduled, false otherwise
 */
bool rtc_wakeup_timer_start(uint32_t seconds, rtc_wakeup_callback_t callback,
                            void* context);

/**
 * @brief Stop the RTC wakeup timer
 */
void rtc_wakeup_timer_stop(void);
