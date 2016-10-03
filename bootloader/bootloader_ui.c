#include "display.h"
#include "bootloader_trezor.h"

void screen_welcome(void)
{
    display_image(0, 0, 240, 240, toi_trezor, sizeof(toi_trezor));
    display_text(0, 240, "bootloader", 10, FONT_MONO, 0xFFFF, 0x0000);
}

void screen_info(void)
{
}

void screen_upload_request(void)
{
}

void screen_upload_progress(int permil)
{
}

void screen_upload_success(void)
{
}

void screen_upload_abort(void)
{
}
