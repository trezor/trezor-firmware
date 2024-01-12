#include <string.h>

#include "flash_otp.h"
#include "model.h"
#include "unit_variant.h"
#include TREZOR_BOARD

static uint8_t unit_variant_color = 0;
static bool unit_variant_btconly = false;
static bool unit_variant_ok = false;

static int16_t unit_variant_build_year = -1;

static void unit_variant_0x01(const uint8_t *data) {
  unit_variant_color = data[1];
  unit_variant_btconly = data[2] == 1;
  unit_variant_ok = true;
}

static int16_t unit_variant_get_build_year(void) {
  uint8_t data[FLASH_OTP_BLOCK_SIZE] = {0};

  secbool result =
      flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, data, FLASH_OTP_BLOCK_SIZE);

  if (sectrue != result || data[0] == 0xFF) {
    return -1;
  }

  /**
   * Expecting format {MODEL_IDENTIFIER}-YYMMDD
   *
   * See also
   * https://docs.trezor.io/trezor-firmware/core/misc/memory.html?highlight=otp#otp
   */

  size_t len = strnlen((char *)data, FLASH_OTP_BLOCK_SIZE);

  for (int i = 0; i < len; i++) {
    if (data[i] == '-') {
      if ((len - (i + 1)) != 6) {
        return -1;
      }
      return ((int16_t)data[i + 1] - (int16_t)'0') * 10 +
             ((int16_t)data[i + 2] - (int16_t)'0');
    }
  }
  return -1;
}

void unit_variant_init(void) {
  uint8_t data[FLASH_OTP_BLOCK_SIZE];

  secbool result = flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, data,
                                  FLASH_OTP_BLOCK_SIZE);

  unit_variant_build_year = unit_variant_get_build_year();

  if (sectrue == result) {
    switch (data[0]) {
      case 0x01:
        unit_variant_0x01(data);
        break;
      default:
        break;
    }
  }
}

uint8_t unit_variant_get_color(void) { return unit_variant_color; }

bool unit_variant_get_btconly(void) { return unit_variant_btconly; }

bool unit_variant_present(void) { return unit_variant_ok; }

bool unit_variant_is_sd_hotswap_enabled(void) {
#ifndef USE_SD_CARD
  return false;
#else
#ifdef TREZOR_MODEL_T
  // early produced TTs have a HW bug that prevents hotswapping of the SD card,
  // lets check the build data and decide based on that
  if (unit_variant_build_year <= 18) {
    return false;
  }
  return true;
#else
  return true;
#endif
#endif
}
