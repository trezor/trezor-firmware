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

#include <sys/backup_ram.h>

#include <util/telemetry.h>

// Versioning for persisted telemetry structure
#define TELEMETRY_DATA_VERSION 0x0001

typedef struct {
  uint16_t version;
  uint8_t initialized;  // 0 = not set, 1 = valid data present
  uint8_t reserved;     // alignment/padding
  float min_temp_c;
  float max_temp_c;
} telemetry_data_t;

static bool telemetry_read(telemetry_data_t* out) {
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

static bool telemetry_write(const telemetry_data_t* data) {
  return backup_ram_write(BACKUP_RAM_KEY_TELEMETRY, BACKUP_RAM_ITEM_PUBLIC,
                          data, sizeof(*data));
}

void telemetry_update_battery_temp(float temp_c) {
  telemetry_data_t data;
  bool have = telemetry_read(&data) && data.initialized == 1;

  if (!have) {
    data.version = TELEMETRY_DATA_VERSION;
    data.initialized = 1;
    data.reserved = 0;
    data.min_temp_c = temp_c;
    data.max_temp_c = temp_c;
    telemetry_write(&data);
    return;
  }

  bool changed = false;
  if (temp_c < data.min_temp_c) {
    data.min_temp_c = temp_c;  // min can only decrease
    changed = true;
  }
  if (temp_c > data.max_temp_c) {
    data.max_temp_c = temp_c;  // max can only increase
    changed = true;
  }

  if (changed) {
    telemetry_write(&data);
  }
}

bool telemetry_get_battery_temp_min_max(float* out_min_c, float* out_max_c) {
  telemetry_data_t data;
  if (!telemetry_read(&data) || data.initialized != 1) {
    return false;
  }
  if (out_min_c) *out_min_c = data.min_temp_c;
  if (out_max_c) *out_max_c = data.max_temp_c;
  return true;
}

#endif
