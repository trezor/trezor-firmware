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

#include TREZOR_BOARD

#include <string.h>

#include "flash_otp.h"
#include "model.h"
#include "unit_properties.h"

// Unit properties driver structure
typedef struct {
  // Set to true if the unit properties are valid
  bool initialized;
  // Cached unit properties data
  unit_properties_t cache;

} unit_properties_driver_t;

// Unit properties driver instance
static unit_properties_driver_t g_unit_properties_driver = {
    .initialized = false,
};

bool unit_properties_init(void) {
  unit_properties_driver_t* drv = &g_unit_properties_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(unit_properties_driver_t));

#ifdef USE_SD_CARD
  drv->cache.sd_hotswap_enabled = true;
#ifdef TREZOR_MODEL_T
  drv->cache.sd_hotswap_enabled = false;
#endif
#endif

  // Properties detection is not fully implemented for emulator.
  // Default values are used.

  drv->initialized = true;

  return true;
}

void unit_properties_get(unit_properties_t* props) {
  unit_properties_driver_t* drv = &g_unit_properties_driver;

  ensure(sectrue * drv->initialized, "Unit properties not initialized");

  *props = drv->cache;
}

const unit_properties_t* unit_properties(void) {
  static bool cache_initialized = false;
  static unit_properties_t cache = {0};

  if (!cache_initialized) {
    unit_properties_get(&cache);
    cache_initialized = true;
  }

  return &cache;
}
