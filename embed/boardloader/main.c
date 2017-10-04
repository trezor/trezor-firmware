#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "sdcard.h"
#include "version.h"

#define IMAGE_MAGIC   0x425A5254 // TRZB
#define IMAGE_MAXSIZE (1 * 64 * 1024 + 7 * 128 * 1024)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv", __FILE__, __LINE__, __FUNCTION__);
}

bool check_sdcard(void)
{
    display_printf("checking for SD card\n");

    if (!sdcard_is_present()) {
        display_printf("no SD card found\n");
        return false;
    }

    display_printf("SD card found\n");

    sdcard_power_on();

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < 1024 * 1024) {
        display_printf("SD card too small\n");
        sdcard_power_off();
        return false;
    }

    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    if (image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, NULL)) {
        display_printf("SD card header is valid\n");
        return true;
    } else {
        display_printf("SD card header is invalid\n");
        return false;
    }
}

static void progress_callback(uint16_t val) {
    display_printf(".");
}

bool copy_sdcard(void)
{
    display_printf("erasing flash ");

    // erase flash (except boardloader)
    if (!flash_erase_sectors(FLASH_SECTOR_BOARDLOADER_END + 1, FLASH_SECTOR_FIRMWARE_END, progress_callback)) {
        display_printf(" failed\n");
        return false;
    }
    display_printf(" done\n");

    display_printf("copying new bootloader from SD card\n");

    sdcard_power_on();

    // copy bootloader from SD card to Flash
    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
    sdcard_read_blocks((uint8_t *)buf, 0, 1);

    image_header hdr;
    if (!image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("invalid header\n");
        sdcard_power_off();
        return false;
    }

    if (!flash_unlock()) {
        display_printf("could not unlock flash\n");
        return false;
    }

    for (int i = 0; i < (HEADER_SIZE + hdr.codelen) / SDCARD_BLOCK_SIZE; i++) {
        sdcard_read_blocks((uint8_t *)buf, i, 1);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            if (!flash_write_word(BOOTLOADER_START + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j])) {
                display_printf("copy failed\n");
                sdcard_power_off();
                flash_lock();
                return false;
            }
        }
    }

    sdcard_power_off();
    flash_lock();

    display_printf("done\n");

    return true;
}

const uint8_t BOARDLOADER_KEY_M = 2;
const uint8_t BOARDLOADER_KEY_N = 3;
static const uint8_t * const BOARDLOADER_KEYS[] = {
#ifdef PRODUCTION_KEYS
    (const uint8_t *)"\x34\x38\x16\x6c\x61\x98\xe1\xb8\x55\x5a\xda\x04\x94\xb6\xda\x25\xee\x4f\xe3\xe9\x09\x21\x8a\x01\x92\x05\x2a\x67\xf2\x26\x98\xbf",
    (const uint8_t *)"\xac\x8a\xb4\x0b\x32\xc9\x86\x55\x79\x8f\xd5\xda\x5e\x19\x2b\xe2\x7a\x22\x30\x6e\xa0\x5c\x6d\x27\x7c\xdf\xf4\xa3\xf4\x12\x5c\xd8",
    (const uint8_t *)"\xce\x0f\xcd\x12\x54\x3e\xf5\x93\x6c\xf2\x80\x49\x82\x13\x67\x07\x86\x3d\x17\x29\x5f\xac\xed\x72\xaf\x17\x1d\x6e\x65\x13\xff\x06",
#else
    (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
    (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
    (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
#endif
};

void check_and_jump(void)
{
    display_printf("checking bootloader\n");

    image_header hdr;

    if (image_parse_header((const uint8_t *)BOOTLOADER_START, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("valid bootloader header\n");
    } else {
        display_printf("invalid bootloader header\n");
        return;
    }

    if (image_check_signature((const uint8_t *)BOOTLOADER_START, &hdr, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N, BOARDLOADER_KEYS)) {
        display_printf("valid bootloader signature\n");
        display_printf("JUMP!\n");
        jump_to(BOOTLOADER_START + HEADER_SIZE);

    } else {
        display_printf("invalid bootloader signature\n");
    }
}

int main(void)
{
    periph_init();

    if (0 != display_init()) {
        __fatal_error("display_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != flash_init()) {
        __fatal_error("flash_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != sdcard_init()) {
        __fatal_error("sdcard_init", __FILE__, __LINE__, __FUNCTION__);
    }

    display_printf("TREZOR Boardloader %d.%d.%d.%d\n", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_BUILD);
    display_printf("==================\n");
    display_printf("starting boardloader\n");

    if (check_sdcard()) {
        if (!copy_sdcard()) {
            __fatal_error("HALT", __FILE__, __LINE__, __FUNCTION__);
        }
    }

    check_and_jump();

    __fatal_error("HALT", __FILE__, __LINE__, __FUNCTION__);

    return 0;
}
