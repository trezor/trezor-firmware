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

typedef struct {
  uint16_t year;   /**< Full year (e.g., 2025) */
  uint8_t month;   /**< Month (1–12) */
  uint8_t day;     /**< Day of the month (1–31) */
  uint8_t hour;    /**< Hour (0–23) */
  uint8_t minute;  /**< Minute (0–59) */
  uint8_t second;  /**< Second (0–59) */
  uint8_t weekday; /**< Weekday (1=Monday to 7=Sunday) */
} rtc_datetime_t;

/**
 * @brief Callback invoked when the RTC wakeup event occurs
 *
 * @param context Context pointer passed to rtc_wakeup_timer_start
 */
typedef void (*rtc_wakeup_callback_t)(void* context);

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
 * @brief Get the current timestamp from the RTC
 *
 * Retrieves the current timestamp as a number of seconds since the device got
 * powered up for the first time. The timestamp is calculated based on the
 * current date and time stored in the RTC.
 *
 * @param timestamp Pointer to a variable where the timestamp will be stored.
 * @return true if the timestamp was successfully retrieved, false otherwise
 */
bool rtc_get_timestamp(uint32_t* timestamp);

/**
 * @brief Set the RTC using discrete time values
 *
 * Sets the RTC date and time using individual components: year, month, day,
 * hour, minute, and second. The weekday is automatically calculated based on
 * the given date.
 *
 * @param year Full year (e.g., 2025). Must be between 2000 and 2099.
 * @param month Month (1–12).
 * @param day Day of the month (1–31).
 * @param hour Hour (0–23).
 * @param minute Minute (0–59).
 * @param second Second (0–59).
 * @return true if the time was successfully set, false otherwise
 */
bool rtc_set(uint16_t year, uint8_t month, uint8_t day, uint8_t hour,
             uint8_t minute, uint8_t second);

/**
 * @brief Get the current RTC time as a structured date and time
 *
 * Reads the RTC date and time registers and returns the result in a
 * structured format.
 *
 * @param datetime Pointer to an rtc_datetime_t struct to hold the result.
 * @return true if the time was successfully retrieved, false otherwise
 */
bool rtc_get(rtc_datetime_t* datetime);

/**
 * @brief Start the RTC wakeup timer
 *
 * Configures the RTC to generate an wakeup interrupt at the specified
 * timestamp. When the event occurs, the provided callback function is called
 * with the given context pointer.
 *
 * @param event_timestamp RTC timestamp to wake up at.
 * @param callback Callback function to be called when the wakeup event occurs.
 * @param context Context pointer to be passed to the callback function.
 * @return true if the wakeup timer was successfully started, false otherwise
 */
bool rtc_wakeup_timer_start(uint32_t event_timestamp,
                            rtc_wakeup_callback_t callback, void* context);

/**
 * @brief Stop the RTC wakeup timer
 */
void rtc_wakeup_timer_stop(void);
