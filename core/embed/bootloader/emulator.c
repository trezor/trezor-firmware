#include <stdio.h>
#include <unistd.h>

#include "bootui.h"
#include "common.h"
#include "display.h"
#include "emulator.h"
#include "flash.h"
#include "rust_ui.h"

uint8_t *FIRMWARE_START = 0;
uint32_t stay_in_bootloader_flag;

void set_core_clock(int) {}

int bootloader_main(void);

bool sector_is_empty(uint8_t sector) {
  const uint8_t *storage = flash_get_address(sector, 0, 0);
  size_t storage_size = flash_sector_size(sector);
  for (size_t i = 0; i < storage_size; i++) {
    if (storage[i] != 0xFF) {
      return false;
    }
  }
  return true;
}

__attribute__((noreturn)) int main(int argc, char **argv) {
  flash_init();
  FIRMWARE_START =
      (uint8_t *)flash_get_address(FLASH_SECTOR_FIRMWARE_START, 0, 0);

  // simulate non-empty storage so that we know whether it was erased or not
  if (sector_is_empty(FLASH_SECTOR_STORAGE_1)) {
    secbool ret = flash_write_word(FLASH_SECTOR_STORAGE_1, 16, 0x12345678);
    (void)ret;
  }

  if (argc == 2 && argv[1][0] == 's') {
    // Run the firmware
    stay_in_bootloader_flag = STAY_IN_BOOTLOADER_FLAG;
  } else if (argc == 4) {
    display_init();
    display_backlight(180);
    screen_fatal_error_rust(argv[1], argv[2], argv[3]);
    display_refresh();
    ui_click();
    exit(0);
  }

  bootloader_main();
  hal_delay(3000);
  jump_to(NULL);
}

void display_set_little_endian(void) {}

void display_reinit(void) {}

void mpu_config_bootloader(void) {}

void mpu_config_off(void) {}

__attribute__((noreturn)) void jump_to(void *addr) {
  bool storage_is_erased = sector_is_empty(FLASH_SECTOR_STORAGE_1) &&
                           sector_is_empty(FLASH_SECTOR_STORAGE_2);

  if (storage_is_erased) {
    printf("STORAGE WAS ERASED\n");
    screen_fatal_error_rust("BOOTLOADER EXIT", "Jumped to firmware",
                            "STORAGE WAS ERASED");
  } else {
    printf("storage was retained\n");
    screen_install_success("STORAGE WAS RETAINED", true, true);
  }
  display_backlight(180);
  display_refresh();
  hal_delay(3000);
  exit(0);
}

void ensure_compatible_settings(void) {}

void main_clean_exit(int code) { exit(code); }
