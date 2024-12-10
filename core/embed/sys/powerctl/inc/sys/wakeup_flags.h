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

#ifndef TREZORHAL_WAKEUP_FLAGS_H
#define TREZORHAL_WAKEUP_FLAGS_H

#include <stdint.h>

// Wakeup flags used to signal the reason of the wakeup
// from the STOP mode

#define WAKEUP_FLAG_BUTTON 0x01  // Button pressed
#define WAKEUP_FLAG_WPC 0x02     // Wireless power charging event
#define WAKEUP_FLAG_BLE 0x04     // Bluetooth connection event
#define WAKEUP_FLAG_NFC 0x08     // NFC event
#define WAKEUP_FLAG_USB 0x10     // USB event
#define WAKEUP_FLAG_TIMER 0x20   // Timer event

// Sets the wakeup flag
void wakeup_flags_set(uint16_t flags);

// Resets all wakeup flags
void wakeup_flags_reset(void);

// Gets current wakeup flags
uint16_t wakeup_flags_get(void);

#endif  // TREZORHAL_WAKEUP_FLAGS_H
