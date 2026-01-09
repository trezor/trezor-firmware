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

#define MAX_DEVICE_SN_SIZE 31

#ifdef SECURE_MODE

/**
 * @brief Initializes module and detects the unit properties
 *
 * @return true if the properties are successfully detected
 * @return false otherwise
 */
bool unit_properties_init(void);

#endif  // SECURE_MODE

typedef struct {
  /**
   * Production lock status indicator.
   * When set to true, the unit properties are locked and cannot be modified.
   * This indicates the device is in production mode and configuration is
   * finalized.
   */
  bool locked;

  /**
   * Unit color identifier.
   * This field contains a hardware-specific color code that is opaque to the
   * firmware. The value is interpreted and displayed by Trezor Suite for user
   * identification purposes.
   */
  uint8_t color;
  /** Validity flag for the color field - set to true when color contains a
   * valid value */
  bool color_is_valid;

  /**
   * Unit packaging type identifier.
   * This field contains a packaging-specific code that is opaque to the
   * firmware. The value is used by Trezor Suite to determine the device's
   * packaging variant.
   */
  uint8_t packaging;
  /** Validity flag for the packaging field - set to true when packaging
   * contains a valid value */
  bool packaging_is_valid;

  /**
   * Bitcoin-only firmware restriction flag.
   * When set to true, indicates this unit is configured to run Bitcoin-only
   * firmware, restricting functionality to Bitcoin-related operations only.
   */
  bool btconly;
  /** Validity flag for the btconly field - set to true when btconly contains a
   * valid value */
  bool btconly_is_valid;

  /**
   * SD card hotswap capability flag.
   * When set to true, indicates the unit supports hot-swapping of SD cards
   * without requiring a system restart or power cycle.
   */
  bool sd_hotswap_enabled;

  /**
   * Type of the battery used in this unit
   *
   * Interpretation is model-specific.
   */
  uint8_t battery_type;
  /** Validity flag for the battery_type field - set to true when battery_type
   * contains a valid value */
  bool battery_type_is_valid;

  /** Device production date */
  struct {
    uint16_t year;
    uint8_t month;
    uint8_t day;
  } production_date;

} unit_properties_t;

/**
 * @brief Gets a copy of unit properties structure
 *
 * Properties are detected just once during the initialization.
 *
 * @param props Pointer to the structure to fill with unit properties
 */
void unit_properties_get(unit_properties_t* props);

/**
 * @brief Gets a pointer to the static unit properties structure
 *
 * @return const unit_properties_t* Pointer to the static unit properties
 * structure
 */
const unit_properties_t* unit_properties(void);

/**
 * @brief Gets the device serial number
 *
 * @param device_sn Buffer to store the device serial number
 * @param max_device_sn_size Maximum size of the device_sn buffer
 * @param device_sn_size Pointer to store the actual size of the serial number
 * @return true if the serial number was successfully retrieved
 * @return false otherwise
 */
bool unit_properties_get_sn(uint8_t* device_sn, size_t max_device_sn_size,
                            size_t* device_sn_size);
