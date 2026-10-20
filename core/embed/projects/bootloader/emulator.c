#include <stdlib.h>

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <unistd.h>

#include <SDL3/SDL.h>

#include <io/display.h>
#include <sec/monoctr.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_otp.h>
#include <sys/logging.h>
#include "bootui.h"

#ifdef LOCKABLE_BOOTLOADER
#include <sec/secret.h>
#endif

#include "emulator.h"
#include "rust_ui_common.h"

#include <io/display_utils.h>
#include <sys/systask.h>
#include <sys/unix/bootutils_emu.h>

LOG_DECLARE(emulator)

#undef FIRMWARE_START

uintptr_t FIRMWARE_START = 0;

int bootloader_main(void);

// assuming storage is single subarea
bool storage_empty(const flash_area_t *area) {
  const uint8_t *storage = flash_area_get_address(area, 0, 0);
  size_t storage_size = flash_area_get_size(area);
  for (size_t i = 0; i < storage_size; i++) {
    if (storage[i] != 0xFF) {
      return false;
    }
  }
  return true;
}

void usage(void) {
  printf("Usage: bootloader-emu [options]\n");
  printf("Options:\n");
  printf("  -a  disable animations\n");
  printf("  -s  stay in bootloader\n");
  printf("  -W  boot with the wipe command (BOOT_COMMAND_WIPE)\n");
#ifdef USE_BOOTARGS_RSOD
  printf("  -R  boot with the RSOD command (BOOT_COMMAND_SHOW_RSOD)\n");
#endif
  printf("  -B FILE  boot with the command and arguments from FILE (the\n");
  printf("           format a previous run wrote to trezor.bootargs)\n");
  printf("  -r DIR  record every screen refresh as PNG into DIR\n");
  printf("  -w  wipe any firmware before booting\n");
  printf("  -e MESSAGE [TITLE [FOOTER]]  display error screen and stop\n");
  printf("  -c COLOR_VARIANT  set color variant\n");
  printf("  -b BITCOIN_ONLY  set bitcoin only flag\n");
  printf("  -i IMAGE_FILE  path to firmware image file to be used\n");
  printf(
      "  -f FIRMWARE  run interaction-less update for the specified image\n");
#ifdef LOCKABLE_BOOTLOADER
  printf("  -l  lock bootloader\n");
#endif
  printf("  -p  print the emulator properties as JSON and exit\n");
  printf("  -h  show this help\n");
  printf("\n");
  printf("On exit, the boot command for the next run is written to\n");
  printf("trezor.bootargs in the profile directory. The exit code tells\n");
  printf("how the run ended: %d reboot, %d jump to firmware, %d power off,\n",
         BOOTUTILS_EMU_EXIT_REBOOT, BOOTUTILS_EMU_EXIT_JUMP,
         BOOTUTILS_EMU_EXIT_POWER_OFF);
  printf("%d halt after RSOD, %d closed by the user (no file written),\n",
         BOOTUTILS_EMU_EXIT_HALT, BOOTUTILS_EMU_EXIT_QUIT);
  printf("%d command line rejected (nothing ran).\n", BOOTUTILS_EMU_EXIT_USAGE);
  printf("TREZOR_EMULATOR_FAST_EXIT=1 skips the delays before exiting.\n");
}

bool load_firmware(const char *filename, uint8_t *hash) {
  // read the first 6 kB of firmware file into a buffer
  FILE *file = fopen(filename, "rb");
  if (!file) {
    printf("Failed to open file '%s'\n", filename);
    return false;
  }
  uint8_t buffer[6 * 1024];
  size_t read = fread(buffer, 1, sizeof(buffer), file);
  fclose(file);
  if (read != sizeof(buffer)) {
    printf("File '%s' does not contain a valid firmware image.\n", filename);
    return false;
  }

  // read vendor and image header
  vendor_header vhdr;
  if (sectrue != read_vendor_header(buffer, sizeof(buffer), &vhdr)) {
    printf("File '%s' does not contain a valid vendor header.\n", filename);
    return false;
  }
  const image_header *hdr = read_image_header(
      buffer + vhdr.hdrlen, FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);
  if (hdr != (const image_header *)(buffer + vhdr.hdrlen)) {
    printf("File '%s' does not contain a valid firmware image.\n", filename);
    return false;
  }

  // hash it into boot_args
  BLAKE2S_CTX ctx;
  blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  blake2s_Update(&ctx, buffer, vhdr.hdrlen + hdr->hdrlen);
  blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

  return true;
}

bool preload_firmware_image(const char *filename) {
  static uint8_t fw_buffer[FIRMWARE_MAXSIZE];

  FILE *file = fopen(filename, "rb");
  if (!file) {
    printf("Failed to open file '%s'\n", filename);
    return false;
  }
  size_t read = fread(fw_buffer, 1, sizeof(fw_buffer), file);
  fclose(file);

  ensure(flash_area_erase(&FIRMWARE_AREA, NULL), NULL);

  return sectrue == flash_area_write_data_padded(&FIRMWARE_AREA, 0, fw_buffer,
                                                 read, 0x0, FIRMWARE_MAXSIZE);
}

// Prints what a test harness needs to interpret the flash file: the
// model and where the storage areas sit inside it. Works from the sector
// layout alone, before the flash file is mapped.
static void print_properties(void) {
  printf("{\"model\": \"%s\", \"storage_areas\": [", MODEL_INTERNAL_NAME);
  for (size_t i = 0; i < ARRAY_LENGTH(STORAGE_AREAS); i++) {
    // storage areas are single subareas, see storage_empty()
    const flash_area_t *area = &STORAGE_AREAS[i];
    printf("%s{\"offset\": %u, \"size\": %u}", i > 0 ? ", " : "",
           (unsigned)flash_sector_size(0, area->subarea[0].first_sector),
           (unsigned)flash_area_get_size(area));
  }
  printf("]}\n");
}

static bool sdl_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_EVENT_QUIT:
      exit(BOOTUTILS_EMU_EXIT_QUIT);
      return false;
    case SDL_EVENT_KEY_UP:
      if (event->key.repeat) {
        return false;
      }
      switch (event->key.key) {
        case SDLK_ESCAPE:
          exit(BOOTUTILS_EMU_EXIT_QUIT);
          return false;
        case SDLK_S:
          display_save("emu");
          return false;
      }
      break;
  }
  return true;
}

#define EMULATOR_OPTSTRING "ahpslewc:b:f:i:r:B:WR"

int main(int argc, char **argv) {
  int opt;

  // The informational options answer before the display opens and before
  // the flash file is mapped, which would create it if missing.
  opterr = 0;
  while ((opt = getopt(argc, argv, EMULATOR_OPTSTRING)) != -1) {
    if (opt == 'p') {
      print_properties();
      exit(0);
    }
    if (opt == 'h') {
      usage();
      exit(0);
    }
  }
  opterr = 1;
  optind = 1;

  SDL_SetEventFilter(sdl_event_filter, NULL);

  display_init(DISPLAY_RESET_CONTENT);
  flash_init();
  flash_otp_init();

  FIRMWARE_START = (uintptr_t)flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  bool display_error = false;
  uint8_t set_variant = 0xff;
  uint8_t color_variant = 0;
  uint8_t bitcoin_only = 0;
  while ((opt = getopt(argc, argv, EMULATOR_OPTSTRING)) != -1) {
    switch (opt) {
      case 'a':
        disable_animation(true);
        break;
      case 's':
        bootargs_set(BOOT_COMMAND_STOP_AND_WAIT, NULL, 0);
        break;
      case 'W': {
        bootutils_wipe_info_t info = {
            .title = "WIPE REQUESTED",
            .message = "Wipe command set by the emulator command line",
            .footer = "",
        };
        bootargs_set(BOOT_COMMAND_WIPE, &info, sizeof(info));
      } break;
#ifdef USE_BOOTARGS_RSOD
      case 'R': {
        systask_postmortem_t pminfo = {
            .reason = TASK_TERM_REASON_ERROR,
            .error =
                {
                    .title = "RSOD REQUESTED",
                    .message = "RSOD command set by the emulator command line",
                    .footer = "",
                },
        };
        bootargs_set(BOOT_COMMAND_SHOW_RSOD, &pminfo, sizeof(pminfo));
      } break;
#endif
      case 'r':
        display_record_start((uint8_t *)optarg, strlen(optarg), 0);
        break;
      case 'B':
        if (!bootargs_emu_load_file(optarg)) {
          exit(BOOTUTILS_EMU_EXIT_USAGE);
        }
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
      case 'i': {
        if (!preload_firmware_image(optarg)) {
          exit(BOOTUTILS_EMU_EXIT_USAGE);
        }
      } break;
      case 'w': {
        if (sectrue != flash_area_erase(&FIRMWARE_AREA, NULL)) {
          exit(BOOTUTILS_EMU_EXIT_USAGE);
        }
      } break;
      case 'f': {
        uint8_t hash[BLAKE2S_DIGEST_LENGTH];
        if (!load_firmware(optarg, hash)) {
          exit(BOOTUTILS_EMU_EXIT_USAGE);
        }
        bootargs_set(BOOT_COMMAND_INSTALL_UPGRADE, hash, sizeof(hash));
      } break;

#ifdef LOCKABLE_BOOTLOADER
      case 'l':
        secret_lock_bootloader();
        break;
#endif
      default:
        usage();
        exit(BOOTUTILS_EMU_EXIT_USAGE);
    }
  }

  // simulate non-empty storage so that we know whether it was erased or
  // not (after option parsing, so that e.g. -h does not touch the flash file)
  if (storage_empty(&STORAGE_AREAS[0])) {
    uint32_t data = 0x12345678;
    secbool ret =
        flash_area_write_data(&STORAGE_AREAS[0], 0, &data, sizeof(data));
    (void)ret;
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
    error_shutdown_ex(title, message, footer);
  }

  // write variant to OTP
  const uint8_t otp_data[] = {set_variant, color_variant, bitcoin_only};
  (void)!flash_otp_write(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, otp_data,
                         sizeof(otp_data));

  int exit_code = bootloader_main();

  char msg[64];
  snprintf(msg, sizeof(msg), "Exit code: %d", exit_code);

  error_shutdown_ex("BOOTLOADER ERROR", msg, "UNEXPECTED EXIT");
  return 0;
}

void jump_to_next_stage(uint32_t address, const startup_args_t *args) {
  bool storage_is_erased =
      storage_empty(&STORAGE_AREAS[0]) && storage_empty(&STORAGE_AREAS[1]);

  if (storage_is_erased) {
    LOG_WARN("Storage was erased");
  } else {
    LOG_WARN("Storage was retained");
  }
  LOG_WARN("Jumped to firmware");

  // The next stage starts with a clean command, as on hardware
  bootargs_set(BOOT_COMMAND_NONE, NULL, 0);
  bootutils_emu_exit(BOOTUTILS_EMU_EXIT_JUMP);
}
