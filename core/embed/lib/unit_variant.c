#include "unit_variant.h"
#include "flash.h"
#include "model.h"

static uint8_t unit_variant_color = 0;
static bool unit_variant_btconly = false;
static bool unit_variant_ok = false;

static void unit_variant_0x01(const uint8_t *data) {
  unit_variant_color = data[1];
  unit_variant_btconly = data[2] == 1;
  unit_variant_ok = true;
}

void unit_variant_init(void) {
  uint8_t data[FLASH_OTP_BLOCK_SIZE];

  secbool result = flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, data,
                                  FLASH_OTP_BLOCK_SIZE);

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
