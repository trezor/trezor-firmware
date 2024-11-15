#include <trezor_model.h>
#include <trezor_rtl.h>

#include <unistd.h>

#include <SDL.h>

#include <io/display.h>
#include <sys/bootargs.h>
#include <sys/systick.h>
#include <util/flash.h>
#include <util/flash_otp.h>
#include "bootui.h"
#include "rust_ui.h"

#ifdef USE_OPTIGA
#include <sec/secret.h>
#endif

#include "emulator.h"

#undef FIRMWARE_START

uint8_t *FIRMWARE_START = 0;

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
  printf("Usage: ./build/bootloader/bootloader_emu [options]\n");
  printf("Options:\n");
  printf("  -s  stay in bootloader\n");
  printf("  -e MESSAGE [TITLE [FOOTER]]  display error screen and stop\n");
  printf("  -c COLOR_VARIANT  set color variant\n");
  printf("  -b BITCOIN_ONLY  set bitcoin only flag\n");
  printf(
      "  -f FIRMWARE  run interaction-less update for the specified image\n");
#ifdef USE_OPTIGA
  printf("  -l  lock bootloader\n");
#endif
  printf("  -h  show this help\n");
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
  if (sectrue != read_vendor_header(buffer, &vhdr)) {
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

static int sdl_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_QUIT:
      exit(3);
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          exit(3);
          return 0;
        case SDLK_p:
          display_save("emu");
          return 0;
      }
      break;
  }
  return 1;
}

__attribute__((noreturn)) int main(int argc, char **argv) {
  SDL_SetEventFilter(sdl_event_filter, NULL);

  display_init(DISPLAY_RESET_CONTENT);
  flash_init();
  flash_otp_init();

  FIRMWARE_START = (uint8_t *)flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  // simulate non-empty storage so that we know whether it was erased or not
  if (storage_empty(&STORAGE_AREAS[0])) {
    secbool ret = flash_area_write_word(&STORAGE_AREAS[0], 16, 0x12345678);
    (void)ret;
  }

  int opt;
  bool display_error = false;
  uint8_t set_variant = 0xff;
  uint8_t color_variant = 0;
  uint8_t bitcoin_only = 0;
  while ((opt = getopt(argc, argv, "hslec:b:f:")) != -1) {
    switch (opt) {
      case 's':
        bootargs_set(BOOT_COMMAND_STOP_AND_WAIT, NULL, 0);
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
      case 'f': {
        uint8_t hash[BLAKE2S_DIGEST_LENGTH];
        if (!load_firmware(optarg, hash)) {
          exit(1);
        }
        bootargs_set(BOOT_COMMAND_INSTALL_UPGRADE, hash, sizeof(hash));
      } break;
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
    error_shutdown_ex(title, message, footer);
  }

  // write variant to OTP
  const uint8_t otp_data[] = {set_variant, color_variant, bitcoin_only};
  (void)!flash_otp_write(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, otp_data,
                         sizeof(otp_data));

  bootloader_main();
  hal_delay(3000);
  jump_to(0);
}

void jump_to(uint32_t address) {
  bool storage_is_erased =
      storage_empty(&STORAGE_AREAS[0]) && storage_empty(&STORAGE_AREAS[1]);

  if (storage_is_erased) {
    printf("STORAGE WAS ERASED\n");
    error_shutdown_ex("BOOTLOADER EXIT", "Jumped to firmware",
                      "STORAGE WAS ERASED");
  } else {
    printf("storage was retained\n");
    error_shutdown_ex("BOOTLOADER EXIT", "Jumped to firmware",
                      "STORAGE WAS RETAINED");
  }
}
