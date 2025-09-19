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

/** Set of wake-up flags */
typedef uint16_t wakeup_flags_t;

#define WAKEUP_FLAG_BUTTON (1 << 0) /** Button pressed */
#define WAKEUP_FLAG_POWER (1 << 1)  /** Power up */
#define WAKEUP_FLAG_BLE (1 << 2)    /** Bluetooth communication */
#define WAKEUP_FLAG_NFC (1 << 3)    /** NFC event */
#define WAKEUP_FLAG_RTC (1 << 4)    /** RTC wake-up timer */
#define WAKEUP_FLAG_USB (1 << 5)    /** USB WIRE communication */

/**
 * @brief Puts device into suspend mode (actually STOP2 mode on STM32U5)
 *
 * @return Return flags indicating the reason for wakeup
 */
wakeup_flags_t system_suspend(void);

/**
 * @brief Set wakeup flags
 * @param flags Wakeup flags to set
 */
void wakeup_flags_set(wakeup_flags_t flags);

/**
 * @brief Reset wakeup flags
 */
void wakeup_flags_reset(void);

/**
 * @brief Get wakeup flags
 * @param flags Pointer to store the current wakeup flags
 */
void wakeup_flags_get(wakeup_flags_t* flags);
