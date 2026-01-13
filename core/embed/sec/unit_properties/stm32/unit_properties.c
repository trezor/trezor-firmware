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

#include <sec/unit_properties.h>

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/flash_otp.h>

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

// Parse two digit number from the string.
//
// Returns -1 if the string is not a valid two-digit number.
static inline int parse_two_digits(const char* str) {
  if (str[0] < '0' || str[0] > '9' || str[1] < '0' || str[1] > '9') {
    return -1;
  }
  return (str[0] - '0') * 10 + (str[1] - '0');
}

// Reads the production date from the OTP block.
//
// Returns `false` in case of and flash read error.
static bool get_production_date(int* year, int* month, int* day) {
  *year = -1;

  uint8_t otp_data[FLASH_OTP_BLOCK_SIZE];

  // Batch block contains a string with the build date.
  // Expecting format {MODEL_IDENTIFIER}-YYMMDD.
  // https://docs.trezor.io/trezor-firmware/core/misc/memory.html?highlight=otp#otp

  if (sectrue != flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, otp_data,
                                FLASH_OTP_BLOCK_SIZE)) {
    return false;
  }

  if (otp_data[0] != 0xFF) {
    char* str = (char*)otp_data;

    // Last 7 characters are the date "-YYMMDD"
    int i = strnlen(str, FLASH_OTP_BLOCK_SIZE) - 7;

    if (i >= 0 && str[i] == '-') {
      *year = parse_two_digits(&str[i + 1]);
      *month = parse_two_digits(&str[i + 3]);
      *day = parse_two_digits(&str[i + 5]);
    }
  }

  return true;
}

// Reads and parses the unit properties from the OTP block.
//
// Returns `false` in case of and flash read error.
static bool detect_properties(unit_properties_t* props) {
  uint8_t otp_data[FLASH_OTP_BLOCK_SIZE];

  props->locked =
      sectrue == flash_otp_is_locked(FLASH_OTP_BLOCK_DEVICE_VARIANT);

  if (sectrue != flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, otp_data,
                                FLASH_OTP_BLOCK_SIZE)) {
    return false;
  }

  if (sectrue == flash_otp_is_locked(FLASH_OTP_BLOCK_DEVICE_VARIANT_REWORK)) {
    uint8_t otp_rework_data[FLASH_OTP_BLOCK_SIZE];
    if (sectrue != flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT_REWORK, 0,
                                  otp_rework_data, FLASH_OTP_BLOCK_SIZE)) {
      return false;
    }
    if (otp_rework_data[0] != 0xFF) {
      memcpy(otp_data, otp_rework_data, sizeof(otp_rework_data));
    }
  }

  switch (otp_data[0]) {
    case 0xFF:
      // OTP block was not written yet, keep the defaults
      break;

    case 0x01:
      // The fields were gradually added to the OTP block over time.
      // Unused trailing bytes were always set to 0x00.
      props->color = otp_data[1];
      props->color_is_valid = true;
      props->btconly = otp_data[2] == 1;
      props->btconly_is_valid = true;
      props->packaging = otp_data[3];
      props->packaging_is_valid = true;
      props->battery_type = otp_data[4];
      props->battery_type_is_valid = true;
      break;

    default:
      // Unknown variant, be conservative and keep the defaults
      break;
  }

  int production_year = 0, production_month = 0, production_day = 0;
  get_production_date(&production_year, &production_month, &production_day);
  props->production_date.year = 2000 + production_year;
  props->production_date.month = production_month;
  props->production_date.day = production_day;

  props->sd_hotswap_enabled = true;
#ifdef TREZOR_MODEL_T2T1
  // Early produced TTs have a HW bug that prevents hotswapping of the SD card,
  // lets check the build data and decide based on that.

  if (production_year <= 18) {
    props->sd_hotswap_enabled = false;
  }
#endif

  return true;
}

bool unit_properties_init(void) {
  unit_properties_driver_t* drv = &g_unit_properties_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(unit_properties_driver_t));

  if (!detect_properties(&drv->cache)) {
    return false;
  }

  drv->initialized = true;

  return true;
}

void unit_properties_get(unit_properties_t* props) {
  unit_properties_driver_t* drv = &g_unit_properties_driver;

  ensure(sectrue * drv->initialized, "Unit properties not initialized");

  *props = drv->cache;
}

bool unit_properties_get_sn(uint8_t* device_sn, size_t max_device_sn_size,
                            size_t* device_sn_size) {
  uint8_t block[FLASH_OTP_BLOCK_SIZE] = {0};
  // The OTP block should contain a null-terminated string when set.
  if (sectrue !=
          flash_otp_read(FLASH_OTP_BLOCK_DEVICE_SN, 0, block, sizeof(block)) ||
      block[0] == 0xFF) {
    return false;
  }

  size_t len = strnlen((char*)block, sizeof(block));
  if (len > max_device_sn_size) {
    return false;
  }

  memcpy(device_sn, block, len);
  *device_sn_size = len;
  return true;
}

#endif  // SECURE_MODE

const unit_properties_t* unit_properties(void) {
  static bool cache_initialized = false;
  static unit_properties_t cache = {0};

  if (!cache_initialized) {
    unit_properties_get(&cache);
    cache_initialized = true;
  }

  return &cache;
}
