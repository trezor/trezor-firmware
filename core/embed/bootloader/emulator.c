#include <stdio.h>
#include <unistd.h>

#include TREZOR_BOARD
#include "boot_internal.h"
#include "bootui.h"
#include "common.h"
#include "display.h"
#include "flash.h"
#include "model.h"
#include "rust_ui.h"
#ifdef USE_OPTIGA
#include "secret.h"
#endif

#include "emulator.h"

#undef FIRMWARE_START

uint8_t *FIRMWARE_START = 0;

// Simulation of a boot command normally grabbed during reset processing
boot_command_t g_boot_command = BOOT_COMMAND_NONE;
// Simulation of a boot args normally sitting at the BOOT_ARGS region
uint8_t g_boot_args[BOOT_ARGS_SIZE];

void set_core_clock(int) {}

int bootloader_main(void);

bool sector_is_empty(uint16_t sector) {
  const uint8_t *storage = flash_get_address(sector, 0, 0);
  size_t storage_size = flash_sector_size(sector);
  for (size_t i = 0; i < storage_size; i++) {
    if (storage[i] != 0xFF) {
      return false;
    }
  }
  return true;
}

void usage(void) {
  printf("Usage: ./build/bootloader/bootloader_emu [options]\n");
  printf("Options:\n");
  printf("  -s  stay in bootloader\n");
  printf("  -e MESSAGE [TITLE [FOOTER]]  display error screen and stop\n");
  printf("  -c COLOR_VARIANT  set color variant\n");
  printf("  -b BITCOIN_ONLY  set bitcoin only flag\n");
#ifdef USE_OPTIGA
  printf("  -l  lock bootloader\n");
#endif
  printf("  -h  show this help\n");
}

__attribute__((noreturn)) void display_error_and_die(const char *message,
                                                     const char *title,
                                                     const char *footer) {
  if (footer == NULL) {
    footer = "PLEASE VISIT\nTREZOR.IO/RSOD";
  }
  if (title == NULL) {
    title = "INTERNAL ERROR";
  }
  display_init();
  display_backlight(180);
  screen_fatal_error_rust(title, message, footer);
  display_refresh();
#if USE_TOUCH
  printf("Click screen to exit.\n");
#elif USE_BUTTON
  printf("Press both buttons to exit.\n");
#endif
  ui_click();
  exit(0);
}

__attribute__((noreturn)) int main(int argc, char **argv) {
  flash_init();
  FIRMWARE_START = (uint8_t *)flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  // simulate non-empty storage so that we know whether it was erased or not
  if (sector_is_empty(STORAGE_AREAS[0].subarea[0].first_sector)) {
    secbool ret = flash_area_write_word(&STORAGE_AREAS[0], 16, 0x12345678);
    (void)ret;
  }

  int opt;
  bool display_error = false;
  uint8_t set_variant = 0xff;
  uint8_t color_variant = 0;
  uint8_t bitcoin_only = 0;
  while ((opt = getopt(argc, argv, "hslec:b:")) != -1) {
    switch (opt) {
      case 's':
        g_boot_command = BOOT_COMMAND_STOP_AND_WAIT;
        break;
      case 'e':
        display_error = true;
        break;
      case 'c':
        set_variant = 1;
        color_variant = atoi(optarg);
        break;
      case 'b':
        set_variant = 1;
        bitcoin_only = atoi(optarg);
        break;
#ifdef USE_OPTIGA
      case 'l':
        // write bootloader-lock secret
        secret_write_header();
        break;
#endif
      default:
        usage();
        exit(1);
    }
  }

  if (display_error) {
    const char *message, *title = NULL, *footer = NULL;
    if (optind < argc) {
      message = argv[optind++];
      if (optind < argc) {
        title = argv[optind++];
        if (optind < argc) {
          footer = argv[optind++];
        }
      }
    } else {
      message = "No message specified";
    }
    display_error_and_die(message, title, footer);
  }

  // write variant to OTP
  const uint8_t otp_data[] = {set_variant, color_variant, bitcoin_only};
  (void)!flash_otp_write(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, otp_data,
                         sizeof(otp_data));

  bootloader_main();
  hal_delay(3000);
  jump_to(NULL);
}

void display_set_little_endian(void) {}

void display_reinit(void) {}

void mpu_config_bootloader(void) {}

void mpu_config_off(void) {}

__attribute__((noreturn)) void jump_to(void *addr) {
  bool storage_is_erased =
      sector_is_empty(STORAGE_AREAS[0].subarea[0].first_sector) &&
      sector_is_empty(STORAGE_AREAS[1].subarea[0].first_sector);

  if (storage_is_erased) {
    printf("STORAGE WAS ERASED\n");
    screen_fatal_error_rust("BOOTLOADER EXIT", "Jumped to firmware",
                            "STORAGE WAS ERASED");
  } else {
    printf("storage was retained\n");
    screen_fatal_error_rust("BOOTLOADER EXIT", "Jumped to firmware",
                            "STORAGE WAS RETAINED");
  }
  display_backlight(180);
  display_refresh();
  hal_delay(3000);
  exit(0);
}

void ensure_compatible_settings(void) {}

void main_clean_exit(int code) { exit(code); }
