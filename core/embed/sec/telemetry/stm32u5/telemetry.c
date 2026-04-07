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

#ifdef SECURE_MODE

#include <trezor_types.h>

#include <sec/backup_ram.h>
#include <sec/telemetry.h>

// Versioning for persisted telemetry structure
#define TELEMETRY_DATA_VERSION 0x0001

typedef struct {
  uint16_t version;
  uint8_t initialized;  // 0 = not set, 1 = valid data present
  uint8_t reserved;     // alignment/padding
  telemetry_data_t data;
} telemetry_t;

static bool telemetry_read(telemetry_t* out) {
  size_t size = 0;
  if (!backup_ram_read(BACKUP_RAM_KEY_TELEMETRY, out, sizeof(*out), &size)) {
    return false;
  }
  if (size != sizeof(*out)) {
    return false;
  }
  if (out->version != TELEMETRY_DATA_VERSION) {
    return false;
  }
  return true;
}

static bool telemetry_write(const telemetry_t* data) {
  return backup_ram_write(BACKUP_RAM_KEY_TELEMETRY, BACKUP_RAM_ITEM_PUBLIC,
                          data, sizeof(*data));
}

static void telemetry_init_record(void) {
  telemetry_t telemetry;
  telemetry.version = TELEMETRY_DATA_VERSION;
  telemetry.initialized = 1;
  telemetry.reserved = 0;
  telemetry.data.min_temp_c = 500.0f;
  telemetry.data.max_temp_c = -500.0f;
  telemetry.data.battery_errors.all = 0;
  telemetry.data.battery_cycles = 0.0f;
  telemetry_write(&telemetry);
}

void telemetry_update_battery_temp(float temp_c) {
  telemetry_t telemetry;
  bool have = telemetry_read(&telemetry) && telemetry.initialized == 1;

  if (!have) {
    telemetry_init_record();
  }

  bool changed = false;
  if (temp_c < telemetry.data.min_temp_c) {
    telemetry.data.min_temp_c = temp_c;  // min can only decrease
    changed = true;
  }
  if (temp_c > telemetry.data.max_temp_c) {
    telemetry.data.max_temp_c = temp_c;  // max can only increase
    changed = true;
  }

  if (changed) {
    telemetry_write(&telemetry);
  }
}

void telemetry_update_battery_errors(telemetry_batt_errors_t errors) {
  telemetry_t telemetry;
  bool have = telemetry_read(&telemetry) && telemetry.initialized == 1;

  if (!have) {
    telemetry_init_record();
  }

  // Only update and write if some of OUR flags are set
  if (errors.all != 0 &&
      ((telemetry.data.battery_errors.all & errors.all) != errors.all)) {
    telemetry.data.battery_errors.all |= errors.all;
    telemetry_write(&telemetry);
  }
}

void telemetry_update_battery_cycles(float battery_cycles_inc) {
  telemetry_t telemetry;
  bool have = telemetry_read(&telemetry) && telemetry.initialized == 1;

  if (!have) {
    telemetry_init_record();
  }

  if (battery_cycles_inc > 0.0f) {
    telemetry.data.battery_cycles += battery_cycles_inc;
    telemetry_write(&telemetry);
  }
}

bool telemetry_get(telemetry_data_t* out) {
  telemetry_t telemetry;
  if (!telemetry_read(&telemetry) || telemetry.initialized != 1) {
    return false;
  }
  if (out != NULL) {
    *out = telemetry.data;
  }
  return true;
}

void telemetry_reset(void) { telemetry_init_record(); }

#endif
