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
#define TELEMETRY_DATA_VERSION_V1 0x0001
#define TELEMETRY_DATA_VERSION_V2 0x0002
#define TELEMETRY_DATA_VERSION TELEMETRY_DATA_VERSION_V2

typedef struct {
  float min_temp_c;
  float max_temp_c;
  telemetry_batt_errors_t battery_errors;
  float battery_cycles;
} telemetry_data_v1_t;

typedef struct {
  uint16_t version;
  uint8_t initialized;  // 0 = not set, 1 = valid data present
  uint8_t reserved;     // alignment/padding
  telemetry_data_v1_t data;
} telemetry_v1_t;

typedef struct {
  uint16_t version;
  uint8_t initialized;  // 0 = not set, 1 = valid data present
  uint8_t reserved;     // alignment/padding
  telemetry_data_t data;
} telemetry_t;

static bool telemetry_write(const telemetry_t* data) {
  return backup_ram_write(BACKUP_RAM_KEY_TELEMETRY, BACKUP_RAM_ITEM_PUBLIC,
                          data, sizeof(*data));
}

static bool telemetry_read(telemetry_t* out) {
  union {
    telemetry_t v2;
    telemetry_v1_t v1;
  } stored = {0};

  size_t size = 0;
  if (!backup_ram_read(BACKUP_RAM_KEY_TELEMETRY, &stored, sizeof(stored),
                       &size)) {
    return false;
  }

  if (size == sizeof(stored.v2) &&
      stored.v2.version == TELEMETRY_DATA_VERSION_V2) {
    *out = stored.v2;
    return true;
  }

  if (size == sizeof(stored.v1) &&
      stored.v1.version == TELEMETRY_DATA_VERSION_V1) {
    telemetry_t migrated = {0};
    migrated.version = TELEMETRY_DATA_VERSION_V2;
    migrated.initialized = stored.v1.initialized;
    migrated.reserved = stored.v1.reserved;
    migrated.data.min_temp_c = stored.v1.data.min_temp_c;
    migrated.data.max_temp_c = stored.v1.data.max_temp_c;
    migrated.data.battery_errors = stored.v1.data.battery_errors;
    migrated.data.battery_cycles = stored.v1.data.battery_cycles;
    migrated.data.tropic_alarms = 0;

    telemetry_write(&migrated);
    *out = migrated;
    return true;
  }

  return false;
}

static void telemetry_init_record(telemetry_t* out) {
  telemetry_t telemetry = {0};
  telemetry.version = TELEMETRY_DATA_VERSION;
  telemetry.initialized = 1;
  telemetry.reserved = 0;
  telemetry.data.min_temp_c = 500.0f;
  telemetry.data.max_temp_c = -500.0f;
  telemetry.data.battery_errors.all = 0;
  telemetry.data.battery_cycles = 0.0f;
  telemetry.data.tropic_alarms = 0;
  telemetry_write(&telemetry);
  if (out != NULL) {
    *out = telemetry;
  }
}

void telemetry_update_battery_temp(float temp_c) {
  telemetry_t telemetry;
  bool have = telemetry_read(&telemetry) && telemetry.initialized == 1;

  if (!have) {
    telemetry_init_record(&telemetry);
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
    telemetry_init_record(&telemetry);
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
    telemetry_init_record(&telemetry);
  }

  if (battery_cycles_inc > 0.0f) {
    telemetry.data.battery_cycles += battery_cycles_inc;
    telemetry_write(&telemetry);
  }
}

void telemetry_update_tropic_alarms(uint32_t tropic_alarms_add) {
  telemetry_t telemetry;
  bool have = telemetry_read(&telemetry) && telemetry.initialized == 1;

  if (!have) {
    telemetry_init_record(&telemetry);
  }

  bool changed = false;
  if (tropic_alarms_add != 0) {
    telemetry.data.tropic_alarms += tropic_alarms_add;
    changed = true;
  }

  if (changed) {
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

void telemetry_reset(void) { telemetry_init_record(NULL); }

#endif
