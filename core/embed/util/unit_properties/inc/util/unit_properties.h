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

#ifndef TREZORHAL_UNIT_PROPERTIES_H
#define TREZORHAL_UNIT_PROPERTIES_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

// Initializes module a detects the unit properties
//
// Returns `true` if the properties are successfully detected
bool unit_properties_init(void);

#endif  // KERNEL_MODE

typedef struct {
  // Set to true if the unit properties are locked and cannot be changed
  // (the device is in the production mode)
  bool locked;

  // Unit color. The value is opaque to the firmware and is
  // used only by Trezor Suite.
  uint8_t color;
  // Set if `color` field contains a valid value
  bool color_is_valid;

  // Unit packaging. The value is opaque for the firmware and is
  // used only by Trezor Suite.
  uint8_t packaging;
  // Set if `packaging` field contains a valid value
  bool packaging_is_valid;

  // Set to true if the unit is BTC only
  bool btconly;
  // Set if `btconly` field contains a valid value
  bool btconly_is_valid;

  // Set to true if the SD card hotswap is enabled
  bool sd_hotswap_enabled;

} unit_properties_t;

// Gets a copy of unit properties structure
//
// Properties are detected just once during the initialization.
void unit_properties_get(unit_properties_t* props);

// Gets a pointer to the static unit properties structure
const unit_properties_t* unit_properties(void);

#endif  // TREZORHAL_UNIT_PROPERTIES_H
