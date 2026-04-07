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

#include <trezor_types.h>

#include <sys/rtc.h>

#define MAX_SCHEDULE_LEN 16

_Static_assert((MAX_SCHEDULE_LEN & (MAX_SCHEDULE_LEN - 1)) == 0,
               "MAX_SCHEDULE_LEN must be a power of 2");

typedef uint32_t rtc_event_id_t;

/**
 * @brief Schedule a wakeup event at specified timestamp
 *
 * Configures the RTC to wake up the system from STOP mode at the specified
 * timestamp. After waking up, callback is called if not NULL otherwise
 * the WAKEUP_FLAG_RTC flag is set. Multiple wakeup events may be scheduled,
 * they will be executed in order of their timestamps and call the specific
 * callbacks.
 *
 * @param wakeup_timestamp RTC timestamp to wake up at.
 * @param callback Callback function to be called when the wakeup event occurs.
 * @param context Context pointer to be passed to the callback function.
 * @param event_id Pointer to a variable where the unique ID of the scheduled
 *                 event will be stored.
 * @return true if the wakeup was successfully scheduled, false otherwise
 */
bool rtc_schedule_wakeup_event(uint32_t wakeup_timestamp,
                               rtc_wakeup_callback_t callback, void* context,
                               rtc_event_id_t* event_id);

/**
 * @brief Cancel the wakeup event and remove it from the rtc schedule
 *
 * @param event_id Unique ID of the wakeup event to be cancelled
 * @return true if the event successfully cancelled and removed from schedule
 */
bool rtc_cancel_wakeup_event(uint32_t event_id);
