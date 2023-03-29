#include <unistd.h>

#include "common.h"
#include "display.h"
#include "flash.h"
#include "rust_ui.h"
#include "bootui.h"
#include "emulator.h"

uint8_t *FIRMWARE_START = 0;
uint32_t stay_in_bootloader_flag;

void set_core_clock(int) {}

int bootloader_main(void);

int main(int argc, char **argv) {
  flash_init();
  FIRMWARE_START =
      (uint8_t *)flash_get_address(FLASH_SECTOR_FIRMWARE_START, 0, 0);

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

  int retval = bootloader_main();
  hal_delay(3000);
  exit(retval);
}

void display_set_little_endian(void) {}

void display_reinit(void) {}

void mpu_config_bootloader(void) {}

void mpu_config_off(void) {}

void jump_to(void *addr) {
  screen_fatal_error_rust("= bootloader =", "Jumped to firmware", "this is ok");
  display_refresh();
  hal_delay(3000);
  exit(0);
}

void ensure_compatible_settings(void) {}

void main_clean_exit(int code) { exit(code); }
