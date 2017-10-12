#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "rng.h"
#include "sdcard.h"

#include "lowlevel.h"
#include "version.h"

#define IMAGE_MAGIC   0x425A5254 // TRZB
#define IMAGE_MAXSIZE (1 * 64 * 1024 + 7 * 128 * 1024)

bool check_sdcard(void)
{
    if (!sdcard_is_present()) {
        return false;
    }

    sdcard_power_on();

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < 1024 * 1024) {
        sdcard_power_off();
        return false;
    }

    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    return image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, NULL);
}

static void progress_callback(uint16_t val) {
    display_printf(".");
}

bool copy_sdcard(void)
{
    display_backlight(255);

    display_printf("copying bootloader from SD card\n");
    display_printf("in 5 seconds ...\n\n");
    display_printf("unplug now if you want to abort\n\n");

    display_printf("5 ");
    hal_delay(1000);
    display_printf("4 ");
    hal_delay(1000);
    display_printf("3 ");
    hal_delay(1000);
    display_printf("2 ");
    hal_delay(1000);
    display_printf("1 ");
    hal_delay(1000);
    display_printf("0!\n\n");

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

    display_printf("done\n\n");
    display_printf("Unplug the device and remove the SD card\n");

    return true;
}

const uint8_t BOARDLOADER_KEY_M = 2;
const uint8_t BOARDLOADER_KEY_N = 3;
static const uint8_t * const BOARDLOADER_KEYS[] = {
#if PRODUCTION
    (const uint8_t *)"\x0e\xb9\x85\x6b\xe9\xba\x7e\x97\x2c\x7f\x34\xea\xc1\xed\x9b\x6f\xd0\xef\xd1\x72\xec\x00\xfa\xf0\xc5\x89\x75\x9d\xa4\xdd\xfb\xa0",
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
    image_header hdr;

    if (!image_parse_header((const uint8_t *)BOOTLOADER_START, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("invalid bootloader header\n");
        return;
    }

    if (image_check_signature((const uint8_t *)BOOTLOADER_START, &hdr, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N, BOARDLOADER_KEYS)) {
        jump_to(BOOTLOADER_START + HEADER_SIZE);
    } else {
        display_printf("invalid bootloader signature\n");
    }
}

int main(void)
{
    __stack_chk_guard = rng_get();

#if PRODUCTION
    flash_set_option_bytes();
#endif

    clear_otg_hs_memory();
    periph_init();

    ensure(0 == display_init(), NULL);
    ensure(0 == flash_init(), NULL);
    ensure(0 == sdcard_init(), NULL);

    if (check_sdcard()) {
        if (!copy_sdcard()) {
            ensure(true == copy_sdcard(), NULL);
        } else {
            for (;;);
        }
    }

    check_and_jump();

    ensure(0, "halt");

    return 0;
}
